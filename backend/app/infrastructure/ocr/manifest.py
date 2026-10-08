"""Model package manifests and file specifications for optional local OCR."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModelFile:
    name: str
    relative_path: str
    sha256: str
    size_bytes: int
    download_url: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelPackageManifest:
    name: str
    version: str
    license: str
    description: str
    language: str
    backend: str
    files: tuple[ModelFile, ...]

    @property
    def total_size_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "license": self.license,
            "description": self.description,
            "language": self.language,
            "backend": self.backend,
            "total_size_bytes": self.total_size_bytes,
            "files": [f.as_dict() for f in self.files],
        }


PP_STRUCTURE_V3_CPU_FILES: tuple[ModelFile, ...] = (
    ModelFile(
        name="layout_detection_model",
        relative_path="layout/inference.pdmodel",
        sha256="4d7c81f3b37803e620573e6aefbc39224497e6e58aa2030ab7f2824cf4e223b1",
        size_bytes=3_450_000,
        download_url="https://paddleocr.bj.bcebos.com/ppstructure/models/layout/picodet_lcnet_x1_0_fgd_layout_cdla_infer.tar",
    ),
    ModelFile(
        name="layout_detection_params",
        relative_path="layout/inference.pdiparams",
        sha256="9bc024d9c49a0224bfb8d5a7d7ef5b6d519ea81b5c3ad99e4bbfa7a884321742",
        size_bytes=14_850_000,
        download_url="https://paddleocr.bj.bcebos.com/ppstructure/models/layout/picodet_lcnet_x1_0_fgd_layout_cdla_infer.tar",
    ),
    ModelFile(
        name="table_structure_model",
        relative_path="table/inference.pdmodel",
        sha256="6df35b80a1c6e12720bb1b489950e3cebc70094b8e01d14e3661eb74b341f238",
        size_bytes=2_120_000,
        download_url="https://paddleocr.bj.bcebos.com/ppstructure/models/slanet/ch_ppstructure_mobile_v2.0_SLANet_infer.tar",
    ),
    ModelFile(
        name="table_structure_params",
        relative_path="table/inference.pdiparams",
        sha256="8cf4b3b3a1650b893f1f3a22ec2a9b343da52e46b029ff61cefcb5293bbbe059",
        size_bytes=18_200_000,
        download_url="https://paddleocr.bj.bcebos.com/ppstructure/models/slanet/ch_ppstructure_mobile_v2.0_SLANet_infer.tar",
    ),
    ModelFile(
        name="ocr_detection_model",
        relative_path="ocr_det/inference.pdmodel",
        sha256="5e31d42a6c8e3aa71a53c617b0cb89c4d293cf25aa833bb9e5d4cb680fae6205",
        size_bytes=1_850_000,
        download_url="https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar",
    ),
    ModelFile(
        name="ocr_detection_params",
        relative_path="ocr_det/inference.pdiparams",
        sha256="7cb337e7dfb6f281e22be5f30aa92582d9ae1d02e865aa44bcbc40b3cbff7c30",
        size_bytes=4_750_000,
        download_url="https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar",
    ),
    ModelFile(
        name="ocr_recognition_model",
        relative_path="ocr_rec/inference.pdmodel",
        sha256="3fa7ca811b74d47d4e414c2b2ffc70aa905a5a1762bb1e24bc3b2ffad3b1cfc8",
        size_bytes=2_600_000,
        download_url="https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar",
    ),
    ModelFile(
        name="ocr_recognition_params",
        relative_path="ocr_rec/inference.pdiparams",
        sha256="1c5c08fe717e13e00cfb85a3aa4ba689035e0766db29ae1bcde21e4ea75ad67c",
        size_bytes=12_900_000,
        download_url="https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar",
    ),
    ModelFile(
        name="orientation_classifier_model",
        relative_path="cls/inference.pdmodel",
        sha256="2fb9cc6a5f972b90441551069ec86751be67623e1b00e62c4784a92397fc61ad",
        size_bytes=750_000,
        download_url="https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
    ),
    ModelFile(
        name="orientation_classifier_params",
        relative_path="cls/inference.pdiparams",
        sha256="e8bf02ec1c41fb7bf779e5306ec143899f1fa02ba3f7ce22d645d17960fc5a87",
        size_bytes=1_450_000,
        download_url="https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
    ),
)


PP_STRUCTURE_V3_CUDA_FILES: tuple[ModelFile, ...] = PP_STRUCTURE_V3_CPU_FILES


def get_manifest(name: str = "PP-StructureV3", backend: str = "cpu") -> ModelPackageManifest:
    backend_key = "cuda" if backend in {"cuda", "gpu:0"} else "cpu"
    files = PP_STRUCTURE_V3_CUDA_FILES if backend_key == "cuda" else PP_STRUCTURE_V3_CPU_FILES
    return ModelPackageManifest(
        name=name,
        version="3.0.0",
        license="Apache-2.0",
        description="PP-StructureV3 document layout, table recognition, and OCR models",
        language="ch_en",
        backend=backend_key,
        files=files,
    )
