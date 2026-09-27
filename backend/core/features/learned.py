import cv2
import numpy as np
from typing import Tuple, List
from loguru import logger
from core.features.extractors import FeatureExtractor, KeypointDescriptors

class KorniaFeatureExtractor(FeatureExtractor):
    """
    Extracts deep features using Kornia's LocalFeature module.
    Default uses KeyNet for detection + HardNet for descriptors (float).
    """

    def __init__(self, n_features: int = 5000):
        self._n_features = n_features
        import torch
        import kornia.feature as KF
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load the pre-trained feature extractor from Kornia
        # KeyNetHardNet is a highly performant combination
        self._local_feature = KF.KeyNetHardNet(
            num_features=self._n_features,
            upright=True
        ).to(self.device).eval()
        
        logger.info(f"Loaded Kornia KeyNetHardNet on {self.device}")

    def detect_and_compute(self, img: np.ndarray) -> KeypointDescriptors:
        import torch
        import kornia.feature as KF
        
        from kornia.utils import image_to_tensor
        # Convert grayscale (H, W) numpy to torch tensor (1, 1, H, W) normalized [0, 1]
        t_img = image_to_tensor(img, keepdim=False).float().to(self.device) / 255.0

        with torch.no_grad():
            lafs, resps, descs = self._local_feature(t_img)

        # Kornia returns LAFs of shape (1, N, 2, 3), descs of shape (1, N, 128)
        lafs = lafs[0].cpu().numpy()  # (N, 2, 3)
        resps = resps[0].cpu().numpy() # (N,)
        descs = descs[0].cpu().numpy() # (N, 128)

        if len(lafs) == 0:
            logger.warning("Kornia: No keypoints detected")
            return KeypointDescriptors([], None)

        kps = []
        for i in range(len(lafs)):
            laf = lafs[i]
            # Center of the local affine frame
            x, y = laf[0, 2], laf[1, 2]
            # Approximate size using trace of affine matrix
            scale = np.sqrt(laf[0, 0]**2 + laf[1, 1]**2)
            kp = cv2.KeyPoint(x=float(x), y=float(y), size=float(scale), response=float(resps[i]))
            kps.append(kp)

        logger.debug(f"Kornia KeyNetHardNet: {len(kps)} keypoints")
        return KeypointDescriptors(kps, descs)

    @property
    def descriptor_type(self) -> str:
        return "float"

    @property
    def name(self) -> str:
        return "DEEP"

def match_lightglue(
    src_kpd: KeypointDescriptors,
    ref_kpd: KeypointDescriptors,
) -> Tuple[List[cv2.DMatch], List[cv2.DMatch], np.ndarray, np.ndarray]:
    """
    Match KeyNetHardNet features using LightGlue.
    Returns (raw_matches, filtered_matches, src_pts, dst_pts).
    Since LightGlue intrinsically filters outliers, raw == filtered.
    """
    import torch
    import kornia.feature as KF
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    logger.info(f"Using LightGlue matcher on {device}")
    lg = KF.LightGlue(features="keynet_affnet_hardnet").to(device).eval()

    # Create dummy LAFs and convert everything to torch tensors
    # KeyNetHardNet LAFs are not strictly required if we just pass coordinates, 
    # but LightGlue expects dicts with 'keypoints' and 'descriptors'
    
    def to_dict(kpd):
        pts = np.float32([kp.pt for kp in kpd.keypoints]) # (N, 2)
        descs = kpd.descriptors # (N, 128)
        return {
            "keypoints": torch.from_numpy(pts).unsqueeze(0).to(device), # (1, N, 2)
            "descriptors": torch.from_numpy(descs).unsqueeze(0).to(device), # (1, N, 128)
            "image_size": torch.tensor([[10000, 10000]]).to(device) # dummy size
        }

    dict1 = to_dict(src_kpd)
    dict2 = to_dict(ref_kpd)

    with torch.no_grad():
        matches = lg(dict1, dict2) # dict with 'matches' and 'scores'
    
    # matches is (1, M, 2) tensor of indices
    match_indices = matches["matches"][0].cpu().numpy() # (M, 2)
    scores = matches["scores"][0].cpu().numpy() # (M,)

    cv_matches = []
    for i in range(len(match_indices)):
        m = cv2.DMatch(
            _queryIdx=int(match_indices[i][0]),
            _trainIdx=int(match_indices[i][1]),
            _distance=float(1.0 - scores[i]) # distance is inverse of score
        )
        cv_matches.append(m)

    src_pts = np.float32([src_kpd.keypoints[m.queryIdx].pt for m in cv_matches])
    dst_pts = np.float32([ref_kpd.keypoints[m.trainIdx].pt for m in cv_matches])

    # For neural matchers, the output is already filtered by the network's confidence
    return cv_matches, cv_matches, src_pts, dst_pts


def match_loftr(
    img_src: np.ndarray,
    img_ref: np.ndarray,
    confidence_threshold: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Match two grayscale images using Kornia's LoFTR (outdoor weights).

    Returns:
        (src_pts, ref_pts, confidences) as numpy arrays.
        src_pts and ref_pts are (N, 2) float32 arrays.
        confidences is (N,) float32.
    """
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        import torch
        import kornia.feature as KF
        try:
            from kornia.image import image_to_tensor
        except ImportError:
            from kornia.utils import image_to_tensor
    except ImportError as e:
        logger.warning(f"PyTorch or Kornia not available for LoFTR: {e}")
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if not torch.cuda.is_available():
        logger.warning("LoFTR is running on CPU; inference may take 20-60s per pair.")

    try:
        matcher = KF.LoFTR(pretrained='outdoor').to(device).eval()
    except Exception as e:
        logger.error(f"Failed to load or download LoFTR model: {e}")
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

    try:
        # Convert to tensors and normalize to [0, 1]
        t_src = image_to_tensor(img_src, keepdim=False).float().to(device) / 255.0
        t_ref = image_to_tensor(img_ref, keepdim=False).float().to(device) / 255.0

        # LoFTR expects (B, 1, H, W)
        if t_src.ndim == 2:
            t_src = t_src.unsqueeze(0).unsqueeze(0)
            t_ref = t_ref.unsqueeze(0).unsqueeze(0)
        elif t_src.ndim == 3:
            t_src = t_src.unsqueeze(0)
            t_ref = t_ref.unsqueeze(0)

        with torch.no_grad():
            result = matcher({"image0": t_src, "image1": t_ref})

        mkpts0 = result["keypoints0"].cpu().numpy().astype(np.float32)
        mkpts1 = result["keypoints1"].cpu().numpy().astype(np.float32)
        conf = result["confidence"].cpu().numpy().astype(np.float32)

        # Filter by confidence
        mask = conf >= confidence_threshold
        return mkpts0[mask], mkpts1[mask], conf[mask]
    except Exception as e:
        logger.error(f"LoFTR matching execution error: {e}")
        return np.zeros((0, 2), dtype=np.float32), np.zeros((0, 2), dtype=np.float32), np.zeros((0,), dtype=np.float32)

