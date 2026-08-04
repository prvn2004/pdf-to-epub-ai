from PIL import Image
from typing import List
from app.models.ocr import ImageBox, CropItem
from app.config import settings

class ImageService:
    @staticmethod
    def crop_images(job_id: str, pageno: int, page_pix, image_boxes: List[ImageBox]) -> List[CropItem]:
        pw, ph = page_pix.width, page_pix.height
        page_img = Image.frombytes("RGB", [pw, ph], page_pix.samples)
        crop_dir = settings.CROPS_DIR / job_id
        crop_dir.mkdir(parents=True, exist_ok=True)

        crops = []
        try:
            for idx, box in enumerate(image_boxes):
                try:
                    x = max(0, min(int(box.x), pw - 1))
                    y = max(0, min(int(box.y), ph - 1))
                    w = int(box.width)
                    h = int(box.height)

                    if w <= 2 or h <= 2 or x >= pw or y >= ph:
                        continue

                    w = max(1, min(w, pw - x))
                    h = max(1, min(h, ph - y))

                    cropped = page_img.crop((x, y, x + w, y + h))

                    max_side = max(cropped.size)
                    if max_side > settings.MAX_CROP_SIDE:
                        resized = cropped.resize(
                            (int(cropped.width * (settings.MAX_CROP_SIDE / max_side)),
                             int(cropped.height * (settings.MAX_CROP_SIDE / max_side))),
                            Image.LANCZOS,
                        )
                        cropped.close()
                        cropped = resized

                    fname = f"page{pageno}_img{idx}.jpg"
                    fpath = crop_dir / fname
                    cropped.save(fpath, format="JPEG", quality=85, optimize=True)
                    cropped.close()

                    crops.append(CropItem(
                        path=str(fpath),
                        rel_path=f"/crops/{job_id}/{fname}",
                        caption=box.caption or "",
                        x=x, y=y, width=w, height=h,
                        px_width=cropped.width, px_height=cropped.height,
                    ))
                except Exception as e:
                    print(f"  [crop warn] page {pageno} img {idx}: {e}")
        finally:
            page_img.close()

        return crops
