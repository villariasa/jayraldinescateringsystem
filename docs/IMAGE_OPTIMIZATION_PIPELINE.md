# Image Optimization & Base64 Compression Standards

## 1. Image Processing Workflow
When catering packages or dishes are uploaded in the desktop client, the system executes an automated image optimization pipeline:

1. **Format Normalization**: Converts various input formats (PNG, WebP, HEIC, TIFF) into standardized JPEG/PNG buffers.
2. **Dynamic Scaling**: Applies high-quality Lanczos resampling with bounding box constraints ($800 \times 800$ pixels max).
3. **Quality Tuning**: Applies adaptive quantization ($Q=82$), stripping unnecessary EXIF metadata to yield optimal $60\text{KB} - 150\text{KB}$ payloads.
4. **Data URI Wrapping**: Encodes binary bytes into `data:image/jpeg;base64,...` strings for instant offline persistence and rendering.
