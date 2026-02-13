# Video to SRT - OCR-based Subtitle Extraction
## Tổng quan (Overview)

Đây là một ứng dụng **FastAPI** sử dụng **PaddleOCR v3** để trích xuất phụ đề từ video và chuyển đổi thành định dạng **SRT**. Ứng dụng hỗ trợ cả việc OCR trực tiếp từ video và trích xuất subtitle streams có sẵn thông qua ffmpeg.

**Tính năng chính:**
- Async/Background processing với progress tracking
- Batch OCR cho GPU optimization
- Modular architecture dễ maintain và extend
- Configurable caching và performance settings
- Production-ready với proper error handling

## Kiến trúc hệ thống (System Architecture)

### Công nghệ sử dụng (Tech Stack)

- **FastAPI 0.128.1**: Web framework cho API endpoints
- **PaddleOCR 2.7.0.3**: Engine OCR chính (hỗ trợ đa ngôn ngữ, stable version)
- **PaddlePaddle 3.0.0**: ML framework backend (optimized for stability)
- **OpenCV (cv2)**: Xử lý video và hình ảnh
- **NumPy**: Xử lý mảng và tính toán
- **FFmpeg/FFprobe**: Phân tích video và trích xuất subtitle streams
- **Pydantic**: Validation và serialization dữ liệu
- **websocket-client**: WebSocket communication cho TTS API
- **uv**: Fast Python package manager for dependency installation

### Các thành phần chính (Main Components)

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI Server                     │
├─────────────────────────────────────────────────────┤
│  GET  /health               → Health check           │
│  POST /extract-srt          → Sync extraction        │
│  POST /extract-srt-async    → Async with progress   │
│  GET  /task/{task_id}       → Check task status     │
│  DELETE /task/{task_id}     → Cleanup task          │
└─────────────────────────────────────────────────────┘
                         ↓
       ┌─────────────────────────────────┐
       │   Subtitle Extraction Pipeline   │
       └─────────────────────────────────┘
                         ↓
       ┌─────────────────┴──────────────────┐
       ↓                                     ↓
┌──────────────────┐              ┌──────────────────┐
│  Stream Extract  │              │   OCR Pipeline   │
│   (FFmpeg fast)  │              │  (PaddleOCR v3)  │
└──────────────────┘              └──────────────────┘
                                          ↓
                         ┌────────────────────────────┐
                         │   Frame Processing:        │
                         │   • Letterbox detection    │
                         │   • ROI extraction         │
                         │   • Hash gating            │
                         │   • CLAHE enhancement      │
                         └────────────────────────────┘
                                          ↓
                         ┌────────────────────────────┐
                         │   Text Assembly:           │
                         │   • Multi-line grouping    │
                         │   • Confidence filtering   │
                         │   • Text normalization     │
                         └────────────────────────────┘
                                          ↓
                         ┌────────────────────────────┐
                         │   SRT Segmentation:        │
                         │   • Debouncing             │
                         │   • Fuzzy matching         │
                         │   • Majority voting        │
                         │   • Cue merging            │
                         └────────────────────────────┘
                                          ↓
                                  ┌─────────────┐
                                  │  SRT Output │
                                  └─────────────┘
```

### Cấu trúc Project (Project Structure)

```
SamplePython/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point
│   ├── api/                      # API routes layer
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/                     # Core configuration
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models/                   # Data models & schemas
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   ├── responses.py
│   │   └── internal.py
│   ├── services/                 # Business logic
│   │   ├── __init__.py
│   │   ├── ocr_service.py
│   │   ├── ffmpeg_service.py
│   │   ├── srt_service.py
│   │   └── video_processor.py
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── text_utils.py
│       ├── hash_utils.py
│       └── image_utils.py
├── requirements.txt
├── setup.py
├── run.py                        # Dev server script
├── .env.example
├── .gitignore
├── README.md
└── USAGE.md
```

## Phân tích chi tiết các module

### 1. Utilities Module (Tiện ích)

#### 1.1 SRT Timestamp Formatting
```python
def srt_timestamp(seconds: float) -> str
```
- **Chức năng**: Chuyển đổi thời gian (giây) sang định dạng SRT `HH:MM:SS,mmm`
- **Xử lý**: Tính toán giờ, phút, giây, millisecond từ tổng số giây
- **Edge case**: Xử lý giá trị âm bằng cách set về 0

#### 1.2 Text Normalization
```python
def normalize_text(s: str) -> str
```
- **Chức năng**: Chuẩn hóa text bằng cách:
- Loại bỏ zero-width space characters (`\u200b`)
- Collapse nhiều khoảng trắng liên tiếp
- Giữ nguyên line breaks
- Xóa dòng trống

#### 1.3 Text Similarity
```python
def similarity(a: str, b: str) -> float
```
- **Thuật toán**: Sử dụng `SequenceMatcher` (Gestalt Pattern Matching)
- **Output**: Tỷ lệ tương đồng từ 0.0 đến 1.0
- **Ứng dụng**: So sánh subtitle giữa các frame để detect thay đổi

### 2. Hash Gating Module (Tối ưu hiệu năng)

#### 2.1 Average Hash (aHash)
```python
def ahash(gray: np.ndarray, size: int = 8) -> int
```
- **Mục đích**: Tạo perceptual hash từ ảnh grayscale
- **Thuật toán**:
1. Resize ảnh về 8x8 pixels
2. Tính giá trị trung bình của tất cả pixels
3. Tạo binary hash: 1 nếu pixel > avg, 0 nếu ngược lại
4. Chuyển bit array thành số nguyên

#### 2.2 Hamming Distance
```python
def hamming64(a: int, b: int) -> int
```
- **Chức năng**: Tính số bit khác nhau giữa 2 hash
- **Sử dụng**: Detect frame tương tự để skip OCR (tiết kiệm tài nguyên)
- **Threshold**: Mặc định ≤ 6 bits khác nhau → coi là frame giống nhau

### 3. Letterbox Detection Module

#### 3.1 Active Region Detection
```python
def detect_active_vertical_region(frame_bgr: np.ndarray) -> Tuple[int, int]
```
- **Mục đích**: Phát hiện và loại bỏ black bars (letterbox) ở trên/dưới video
- **Thuật toán**:
1. Chuyển sang grayscale và downscale (tối ưu)
2. Detect black pixels (luma ≤ 18)
3. Tính tỷ lệ black pixels mỗi hàng
4. Tìm top/bottom bars (≥98% pixels đen)
5. Validate bars không quá lớn (<25% video height)
- **Lợi ích**: Giảm vùng OCR, tăng độ chính xác

#### 3.2 ROI Enhancement
```python
def enhance_roi(roi_bgr: np.ndarray) -> np.ndarray
```
- **Thuật toán**: CLAHE (Contrast Limited Adaptive Histogram Equalization)
- **Áp dụng**: Trên L channel của LAB color space
- **Tham số**: clipLimit=2.0, tileGridSize=(8,8)
- **Mục đích**: Tăng độ tương phản subtitle, cải thiện OCR accuracy

### 4. PaddleOCR Integration Module (`app/services/ocr_service.py`)

#### 4.1 OCR Engine Caching
```python
@dataclass
class OcrEntry:
   engine: PaddleOCR
   lock: threading.Lock
   last_used: float
```
- **Tại sao cần cache?**: Khởi tạo PaddleOCR engine rất tốn thời gian
- **Strategy**: LRU cache với configurable max (default 4)
- **Thread-safe**: Mỗi engine có riêng lock để xử lý concurrent requests
- **Cache key**: Dựa trên (lang, device, det_model, rec_model, use_textline_orientation)
- **Configuration**: Set via `OCR_CACHE_MAX` environment variable

#### 4.2 OCR Execution
```python
def run_ocr(entry: OcrEntry, img_bgr: np.ndarray) -> Tuple[List[str], List[float], Optional[np.ndarray]]
def run_ocr_batch(entry: OcrEntry, img_bgr_list: List[np.ndarray]) -> List[Tuple[...]]
```
- **Single mode**: Process one image at a time
- **Batch mode**: Process multiple images together (GPU optimization)
- Automatically enabled when `device="gpu:*"` and `BATCH_OCR_SIZE > 1`
- Configurable batch size via `BATCH_OCR_SIZE` environment variable (default: 8)
- **Input**: BGR image(s) từ OpenCV
- **Processing**: 
1. Convert BGR → RGB (PaddleOCR yêu cầu)
2. Gọi `engine.ocr()` với thread lock
3. Parse kết quả: texts, confidence scores, polygons
- **Output**: Danh sách text lines + scores + polygon coordinates

#### 4.3 Text Assembly
```python
def assemble_subtitle_text(texts, scores, polys, conf_min, line_y_gap_px=18) -> str
```
- **Chức năng**: Ghép nhiều text boxes thành subtitle hoàn chỉnh
- **Logic**:
1. Filter theo confidence threshold (mặc định 0.5)
2. Sắp xếp theo tọa độ Y (top→bottom), sau đó X (left→right)
3. Group các text cùng hàng (Y gap ≤ 18px)
4. Join text trong mỗi hàng bằng space
5. Normalize toàn bộ text

### 5. FFmpeg Integration Module

#### 5.1 Subtitle Stream Detection
```python
def probe_subtitle_streams(video_path: str) -> List[dict]
```
- **Tool**: ffprobe
- **Command**: Lấy thông tin tất cả subtitle streams
- **Output**: JSON với stream index, codec, language
- **Use case**: Fast-path extraction khi video có embedded subtitles

#### 5.2 Stream Extraction
```python
def extract_stream_subtitle_to_srt(video_path, out_srt_path, stream_index=0)
```
- **Tool**: ffmpeg
- **Chức năng**: Trích xuất subtitle stream và convert sang SRT
- **Ưu điểm**: Nhanh hơn OCR hàng trăm lần
- **Nhược điểm**: Chỉ work với video có sẵn subtitle streams

### 6. SRT Segmentation Module (Thuật toán phức tạp nhất)

#### 6.1 Cue Draft (Subtitle Segment)
```python
@dataclass
class CueDraft:
   start: float
   last: float
   text_votes: Counter
```
- **Purpose**: Tạm giữ thông tin một subtitle cue đang được xây dựng
- **Majority voting**: Dùng Counter để track text xuất hiện nhiều nhất
- **Time range**: Track start time và last observation time

#### 6.2 Debouncing Logic
**Vấn đề**: OCR có thể cho kết quả không ổn định giữa các frame liên tiếp

**Giải pháp**: Dual debouncing
1. **Text debounce** (`debounce_frames=2`):
  - Khi detect text mới, đợi 2 frames liên tiếp confirm
  - Tránh false positive từ OCR noise

2. **Empty debounce** (`empty_debounce_frames=2`):
  - Khi không detect text, đợi 2 frames liên tiếp
  - Tránh mất subtitle do 1 frame OCR fail

#### 6.3 Fuzzy Matching
```python
if similarity(subtitle, cur_best) >= req.sim_thr:  # default 0.90
   accept_text_at(t_sec, subtitle)
```
- **Threshold**: 90% similarity
- **Lợi ích**: 
- Cho phép typo nhỏ từ OCR
- Xử lý variations trong cách OCR đọc cùng 1 text
- Tránh tạo nhiều cues cho cùng subtitle

#### 6.4 Cue Merging
```python
def merge_and_filter_cues(cues, min_duration_ms, merge_gap_ms, sim_thr)
```
- **Filter 1**: Loại bỏ cues quá ngắn (<400ms mặc định)
- **Filter 2**: Merge các cues liên tiếp:
- Cùng text (similarity ≥ 90%)
- Gap nhỏ (≤250ms mặc định)
- **Kết quả**: Subtitles mượt mà, không bị fragmented

### 7. FastAPI Endpoints (`app/api/routes.py`)

#### 7.1 Health Check
```python
@router.get("/health")
def health()
```
- Simple liveness probe cho load balancers
- **Response**: `{"status": "ok"}`

#### 7.2 Synchronous Extract SRT Endpoint
```python
@router.post("/extract-srt", response_model=ExtractResponse)
def extract_srt(req: ExtractRequest)
```
- **Behavior**: Blocking request, trả về kết quả ngay
- **Use case**: Small videos, immediate results needed
- **Processing**: Runs extraction on main thread
- **Timeout**: Depends on video duration and device

#### Synchronous Full-FPS Extract SRT Endpoint

```python
@router.post("/extract-srt-frames", response_model=ExtractResponse)
def extract_srt_frames(req: ExtractRequest)
```
- **Purpose**: Run OCR on every sampled frame at `target_fps`. This endpoint samples frames at the configured `target_fps` across the whole video and runs OCR on each sampled frame. When OCR text for consecutive sampled frames is identical (or similar above `sim_thr`), those frames are merged into a single SRT cue spanning their combined time range.
- **Behavior**: Blocking, exhaustive OCR on sampled frames (visual frame-gating is effectively disabled for skipping OCR). Cue assembly relies on textual matching rather than visual hash gating.
- **Use case**: Detect short-lived text and ensure textual continuity is used for grouping. Useful when visual similarity heuristics miss rapid text changes that are best handled by comparing textual output.
- **Processing**:
  1. Sample frames at `target_fps`.
  2. Run OCR on each sampled frame (batching allowed when using GPU).
  3. Compare consecutive OCR outputs using `sim_thr` and `debounce_frames` rules; identical/similar text extends the current cue end time.
  4. Apply final cleanup (`min_duration_ms`, `merge_gap_ms`).
- **Key differences vs `/extract-srt`**:
  - `hash_dist_thr`-based visual skipping is not used to avoid skipping OCR calls; OCR is performed on every sampled frame.
  - Merging is performed on textual similarity across sampled frames.
- **Parameters**: Uses the same input parameters as `/extract-srt` (see models and USAGE for full list). `stats.mode` in the response will be set to `full-fps-ocr` to identify this processing mode.

#### 7.3 Asynchronous Extract SRT Endpoint
```python
@router.post("/extract-srt-async")
async def extract_srt_async(req: ExtractRequest, background_tasks: BackgroundTasks)
```
- **Behavior**: Non-blocking, returns task_id immediately
- **Progress tracking**: Check status via `/task/{task_id}`
- **Use case**: Large videos, multiple concurrent requests
- **Response**: `{"task_id": "...", "status": "processing", "message": "..."}`

#### 7.4 Task Management Endpoints
```python
@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str)

@router.delete("/task/{task_id}")
async def delete_task(task_id: str)
```
- **Status**: `processing`, `completed`, `failed`
- **Progress**: 0.0 to 1.0 (percentage)
- **Result**: Full ExtractResponse when completed
- **Cleanup**: DELETE endpoint removes task from tracking

#### 7.5 Video Blur Endpoint
```python
@router.post("/blur")
def blur(req: BlurRequest)
```
- **Purpose**: Làm mờ các vùng video dựa trên tọa độ (dùng để ẩn phụ đề gốc)
- **GPU Support**: Hỗ trợ GPU acceleration (AMD AMF, NVIDIA NVENC)
- **Output**: Video được xử lý với hậu tố "blurred"

**Parameters**:

| Parameter | Type | Default | Range/Type | Description |
|-----------|------|---------|------------|-------------|
| `video_path` | string | - | path | Đường dẫn video trên server |
| `srt_detail` | list[obj] | - | coordinates | Danh sách region cần blur với tọa độ `{x1, y1, x2, y2}` |
| `blur_strength` | int | 25 | 1-100 | Độ mạnh blur (1=nhẹ, 100=rất mạnh) |
| `output_suffix` | string | "blurred" | string | Hậu tố file output |
| `use_gpu` | bool | true | true/false | Bật GPU acceleration nếu khả dụng |

**Example SRT Detail Object**:
```python
{
  "x1": 100,      # Tọa độ X góc trên-trái
  "y1": 950,      # Tọa độ Y góc trên-trái
  "x2": 1820,     # Tọa độ X góc dưới-phải
  "y2": 1050      # Tọa độ Y góc dưới-phải
}
```

#### 7.6 Video Subtitle Endpoint
```python
@router.post("/subtitle")
def subtitle(req: SubtitleRequest)
```
- **Purpose**: Thêm phụ đề SRT vào video
- **GPU Support**: Hỗ trợ GPU acceleration
- **Output**: Video được xử lý với hậu tố "subtitled"

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_path` | string | - | Đường dẫn video trên server |
| `srt_path` | string | - | Đường dẫn file SRT cần thêm |
| `output_suffix` | string | "subtitled" | Hậu tố file output |
| `use_gpu` | bool | true | Bật GPU acceleration nếu khả dụng |

#### 7.7 Blur and Subtitle Combined Endpoint
```python
@router.post("/blur-and-subtitle")
def blur_and_subtitle(req: BlurAndSubtitleRequest)
```
- **Purpose**: Kết hợp cả hai thao tác (tối ưu hiệu năng)
- **Advantage**: Xử lý video một lần thay vì hai lần
- **Output**: Video được xử lý với hậu tố "vnsrt"

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `video_path` | string | - | Đường dẫn video trên server |
| `srt_path` | string | - | Đường dẫn file SRT cần thêm |
| `srt_detail` | list[obj] | - | Danh sách region cần blur với tọa độ |
| `blur_strength` | int | 25 | Độ mạnh blur (1-100) |
| `output_suffix` | string | "vnsrt" | Hậu tố file output |
| `use_gpu` | bool | true | Bật GPU acceleration nếu khả dụng |

#### 7.8 TTS Audio Synthesis Endpoint
```python
@router.post("/tts/generate", response_model=TTSGenerateResponse)
def tts_generate(req: TTSGenerateRequest)
```
- **Purpose**: Tổng hợp âm thanh từ phụ đề SRT
- **Processing**:
  1. Parse SRT content thành subtitle blocks
  2. Download audio từ TTS API cho mỗi subtitle
  3. Merge audio files theo thứ tự SRT timeline
  4. Return merged audio (optional: base64)
- **Prerequisites**: TTS_ENABLED=true, valid API credentials

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `srt_content` | string | - | SRT subtitle content (full text) |
| `tts_voice` | string | "BV074_streaming" | Voice identifier cho TTS synthesis |
| `output_filename` | string | auto-generated | Tên file audio output (ví dụ: "output.wav") |
| `return_base64` | bool | true | Return audio dưới dạng base64 encoded string |

**Available TTS Voices**:
- `BV074_streaming` - Default voice (Vietnamese)
- `BV104_streaming` - Alternative voice (Vietnamese)
- Các voice khác tùy thuộc vào TTS API provider

**Response**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",
  "audio_filename": "output_audio.wav",
  "audio_path": "/path/to/tts_output/output_audio.wav",
  "audio_base64": "UklGRiY...",  # Base64 if return_base64=true
  "duration_ms": 9000,
  "size_bytes": 144000,
  "message": "Audio synthesis completed successfully"
}
```

#### Subtitle Extraction Request Parameters (23 tunable parameters):

| # | Category | Parameter | Type | Default | Range | Description |
|---|----------|-----------|------|---------|-------|-------------|
| 1 | **Input** | `video` | string | - | path | Đường dẫn video trên server (required) |
| 2 | **Sampling** | `target_fps` | float | 4.0 | 0.1-30.0 | FPS lấy mẫu frame từ video (cao hơn = accuracy tốt hơn nhưng chậm) |
| 3 | | `bottom_start` | float | 0.55 | 0.0-1.0 | % chiều cao bắt đầu ROI (0.55 = 55% từ trên, dùng để skip phần trên video) |
| 4 | | `max_width` | int | 1280 | 320-3840 | Max width sau khi scale frame (giảm để tăng tốc độ, tăng để tăng độ chính xác) |
| 5 | | `enhance` | bool | true | true/false | Bật CLAHE enhancement trước OCR (tăng contrast subtitle) |
| 6 | **OCR Config** | `lang` | string | "vi" | "vi","en","zh","ja",... | Ngôn ngữ OCR (auto-selects PP-OCRv5 model) |
| 7 | | `device` | string | "cpu" | "cpu","gpu:0","gpu:1",... | Device xử lý (CPU hoặc GPU index, GPU nhanh hơn ~3-4x) |
| 8 | | `det_model` | string | "PP-OCRv5_mobile_det" | model_name | Text detection model (legacy, không dùng trong v3.x - auto select theo lang) |
| 9 | | `rec_model` | string | "PP-OCRv5_mobile_rec" | model_name | Text recognition model (legacy, không dùng trong v3.x - auto select theo lang) |
| 10 | | `use_textline_orientation` | bool | false | true/false | Detect và xử lý text xoay/rotated text (chậm hơn) |
| 11 | | `conf_min` | float | 0.5 | 0.0-1.0 | Confidence threshold cho OCR results (cao hơn = kết quả chính xác hơn nhưng ít text) |
| 12 | **Frame Gating** | `hash_dist_thr` | int | 6 | 0-64 | Hamming distance threshold (skip frame nếu < threshold, tiết kiệm OCR 60-80%) |
| 13 | | `content_change_thr` | float | 0.12 | 0.0-1.0 | Threshold detect thay đổi nội dung text (low = sensitive, high = stable) |
| 14 | | `text_motion_thr` | float | 0.08 | 0.0-1.0 | Threshold detect chuyển động/transition text (skip khi text di chuyển) |
| 15 | | `text_presence_thr` | float | 0.30 | 0.0-1.0 | Threshold detect sự thay đổi presence text (xuất hiện/mất) |
| 16 | | `intensity_spike_thr` | float | 0.25 | 0.0-1.0 | Threshold detect intensity spike (sudden changes, scene transitions) |
| 17 | **Debounce** | `debounce_frames` | int | 2 | 1-10 | Số frame confirm khi detect text thay đổi (cao hơn = bỏ false positive) |
| 18 | | `empty_debounce_frames` | int | 2 | 1-10 | Số frame confirm khi detect empty frame (cao hơn = ít bỏ subtitle) |
| 19 | | `sim_thr` | float | 0.90 | 0.5-1.0 | Similarity threshold cho fuzzy matching (low = cho phép typo, high = exact match) |
| 20 | **SRT Cleanup** | `min_duration_ms` | int | 400 | 0-5000 | Minimum subtitle duration (loại bỏ cues quá ngắn < 400ms) |
| 21 | | `merge_gap_ms` | int | 250 | 0-3000 | Max gap để merge liên tiếp cues (nếu gap < 250ms thì merge) |
| 22 | **Output** | `output_path` | string | null | path | Đường dẫn save file SRT trên server (optional, nếu null thì chỉ return SRT text) |
| 23 | | `prefer_subtitle_stream` | bool | false | true/false | Ưu tiên extract embedded subtitle stream qua ffmpeg thay vì OCR (nhanh hơn 20x) |

**Usage Tips**:
- **Tăng tốc độ**: Giảm `target_fps`, tăng `hash_dist_thr`, giảm `max_width`, sử dụng GPU
- **Tăng độ chính xác**: Tăng `target_fps`, tăng `max_width`, giảm `conf_min`, tăng `debounce_frames`
- **Cứu video có letterbox**: Tự động detect, giảm vùng OCR 20-40%
- **Subtitle quá fragmented**: Tăng `merge_gap_ms`, giảm `sim_thr`

**Processing Pipeline**:

```
1. Kiểm tra file tồn tại
2. [Optional] Thử extract subtitle stream qua ffmpeg
3. [OCR Path]:
  a. Khởi tạo/lấy OCR engine từ cache
  b. Mở video với OpenCV
  c. Detect letterbox từ frame đầu
  d. Loop qua frames:
     - Sample theo target_fps
     - Crop ROI (active region + bottom portion)
     - Downscale về max_width
     - [Optional] CLAHE enhancement
     - Hash gating check (skip nếu giống frame trước)
     - OCR execution
     - Assemble subtitle text
     - Debounce + fuzzy matching
     - Update cue segments
  e. Finalize cuối cùng
  f. Merge và filter cues
  g. Convert sang SRT format
4. [Optional] Ghi file SRT
5. Return response với SRT text + stats
```

**Response**:
```json
{
"srt": "1\n00:00:01,000 --> 00:00:03,500\nSubtitle text here\n\n2\n...",
"stats": {
   "mode": "ocr",
   "frames_seen": 7200,
   "frames_sampled": 1200,
   "frames_hashed_skipped": 800,
   "frames_ocr": 400,
   "cues": 150,
   "timing_ms": {
     "total": 45000,
     "decode": 5000,
     "ocr": 38000
   },
   "video": {
     "width": 1920,
     "height": 1080,
     "src_fps": 30.0,
     "active_top": 140,
     "active_bottom": 940
   }
}
}
```

## Các kỹ thuật tối ưu hiệu năng

### 1. Hash-based Frame Skipping
- **Tiết kiệm**: 60-80% OCR calls
- **Trade-off**: Có thể miss subtitle changes nếu hash quá aggressive

### 2. OCR Engine Caching
- **Tiết kiệm**: Hàng giây khởi tạo mỗi request
- **Memory**: Max 4 engines trong RAM

### 3. ROI Optimization
- **Letterbox removal**: Giảm 20-40% diện tích OCR
- **Bottom-only**: Giảm thêm 50% nếu subtitle luôn ở dưới
- **Downscaling**: Balance giữa accuracy và speed

### 4. Adaptive Sampling
- **Dynamic FPS**: Không cần OCR 30fps → 4fps đủ
- **Step calculation**: Tự động tính dựa trên source FPS

### 5. Early Termination
- **Subtitle stream**: Detect và dùng embedded subtitles khi có

## Điểm mạnh của thiết kế

1. **Highly Configurable**: 22 parameters cho fine-tuning
2. **Multi-language**: Support qua PaddleOCR lang parameter
3. **Robust Segmentation**: Debouncing + fuzzy matching + majority voting
4. **Production-ready**: Thread-safe caching, proper error handling
5. **Hybrid Approach**: Fast-path (stream) + OCR fallback
6. **Optimized**: Multiple layers của performance optimization

## Cải tiến đã thực hiện

### Đã implement

1. ** Async/await support**: Background tasks với progress tracking
  - **Implementation**: `/extract-srt-async` endpoint
  - **Features**: Real-time progress updates, non-blocking processing
  - **Code**: `app/api/routes.py`

2. ** Batch OCR processing**: GPU optimization
  - **Implementation**: `OcrService.run_ocr_batch()`
  - **Auto-enable**: Khi `device="gpu:*"`
  - **Configurable**: `BATCH_OCR_SIZE` environment variable
  - **Code**: `app/services/ocr_service.py`

3. ** Configurable caching**: Flexible memory management
  - **Implementation**: `OCR_CACHE_MAX` environment variable
  - **Default**: 4 engines, có thể tăng/giảm theo nhu cầu
  - **Code**: `app/core/config.py`

4. ** Modular architecture**: Clean separation of concerns
  - **Structure**: Layered architecture (API → Services → Utils)
  - **Benefits**: Easy testing, maintainability, scalability
  - **Code**: `app/` package structure

5. ** Progress tracking**: Real-time status updates
  - **Implementation**: Task storage với progress callbacks
  - **Granular**: Updates at 5%, 15%, 20%, 90%, 95%, 98%, 100%
  - **Code**: `app/services/video_processor.py`

### Cải tiến tiếp theo

1. **Parallel frame decoding**: Multi-threaded video reading
  - **Goal**: Tận dụng multi-core CPU
  - **Approach**: ThreadPoolExecutor for frame extraction

2. **Remote storage support**: S3, Azure Blob, GCS
  - **Goal**: Support cloud-based videos
  - **Approach**: Abstract VideoSource interface

3. **Distributed processing**: Multi-worker coordination
  - **Goal**: Scale horizontally
  - **Approach**: Redis for task queue, shared state

4. **Model optimization**: Quantization, pruning
  - **Goal**: Faster inference, lower memory
  - **Approach**: ONNX export, TensorRT

5. **Caching strategies**: Frame-level caching
  - **Goal**: Avoid re-processing same videos
  - **Approach**: Hash-based frame cache

## Use Cases

### 1. Video Platform
- Tự động generate subtitles cho user-uploaded videos
- Support multi-language content

### 2. Accessibility
- Tạo closed captions cho video không có subtitles
- Hỗ trợ người khiếm thính

### 3. Content Archival
- Extract text từ old videos/films
- Digitize legacy content

### 4. Translation Pipeline
- Extract original subtitles → translate → create new SRT

### 5. TTS Service Module (`app/services/tts_service.py`)

#### 5.1 Text-to-Speech Audio Synthesis
- **Mục đích**: Tổng hợp âm thanh từ subtitle bằng WebSocket API
- **API**: Kết nối WebSocket để download audio từ TTS service
- **Batch Processing**: Hỗ trợ xử lý theo lô cho tối ưu hóa hiệu năng
- **Retry Logic**: Tự động retry khi kết nối thất bại (retriable errors)

#### 5.2 SRT Parsing
```python
parse_srt_content(srt_content: str) -> List[Dict]
```
- **Chức năng**: Phân tích nội dung SRT thành các đối tượng subtitle
- **Output**: Danh sách các subtitle với fields: `sequence`, `start`, `end`, `text`
- **Validation**: Kiểm tra format SRT và xử lý các dòng trống

#### 5.3 Audio File Merging
```python
merge_wav_files(wav_files: List[str], output_path: str) -> bool
```
- **Mục đích**: Gộp nhiều file WAV thành một file duy nhất
- **Công cụ**: FFmpeg concat demuxer (lossless merge)
- **Thứ tự**: Giữ nguyên thứ tự file theo SRT sequence

#### 5.4 Base64 Encoding
```python
encode_wav_to_base64(wav_path: str) -> str
```
- **Chức năng**: Mã hóa file WAV sang base64 để trả về trong API response
- **Tiện ích**: Cho phép clients nhận audio data trực tiếp mà không cần tải file riêng

## Cài đặt và sử dụng

### Requirements

**Option 1: Using uv (Recommended - Faster)**
```bash
# Install uv if not already installed
pip install uv

# Clone hoặc cd vào project directory
cd d:\\LEARN\\video-to-srt

# Install dependencies with uv
uv pip install -r requirements.txt
```

**Option 2: Using pip (Traditional)**
```bash
# Clone hoặc cd vào project directory
cd d:\\LEARN\\video-to-srt

# Tạo virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Cài đặt FFmpeg
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download từ https://ffmpeg.org/download.html
```

### Configuration (Optional)

```bash
# Copy environment template
copy .env.example .env

# Edit .env file with your settings
# Example configurations:
# LOG_LEVEL=WARNING            # Suppress debug logs (ERROR, WARNING, INFO, DEBUG)
# OCR_CACHE_MAX=8              # Cache up to 8 OCR engines
# BATCH_OCR_SIZE=16            # GPU batch size
# DEFAULT_TARGET_FPS=6.0       # 6 FPS for faster processing
```

**Note:** By default, `LOG_LEVEL=WARNING` suppresses verbose PaddleOCR debug output. See [LOGGING.md](LOGGING.md) for detailed logging configuration options.

### Chạy server

#### Development mode (auto-reload) - Using uv
```bash
uv run python run.py
```

#### Development mode - Using traditional Python
```bash
python run.py
```

#### Production mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

#### Với custom environment variables (uv)
```bash
# Windows
set OCR_CACHE_MAX=8 && set BATCH_OCR_SIZE=16 && uv run python run.py

# Linux/Mac
OCR_CACHE_MAX=8 BATCH_OCR_SIZE=16 uv run python run.py
```

#### Với custom environment variables (traditional)
```bash
# Windows
set OCR_CACHE_MAX=8
set BATCH_OCR_SIZE=16
python run.py

# Linux/Mac
OCR_CACHE_MAX=8 BATCH_OCR_SIZE=16 python run.py
```

### API Call Examples

#### Synchronous (Blocking)
```python
import requests

# Sync extraction - wait for completion
response = requests.post(
   "http://localhost:8000/extract-srt",
   json={
       "video": "D:/videos/video.mp4",
       "lang": "vi",
       "target_fps": 4.0,
       "conf_min": 0.6,
       "output_path": "D:/output/output.srt"
   }
)

result = response.json()
print(result["srt"])
print(result["stats"])
```

#### Asynchronous (Non-blocking with Progress)
```python
import requests
import time

# Start async task
response = requests.post(
   "http://localhost:8000/extract-srt-async",
   json={
       "video": "D:/videos/long_video.mp4",
       "lang": "vi",
       "device": "gpu:0",
       "output_path": "D:/output/output.srt"
   }
)

task_id = response.json()["task_id"]
print(f"Task started: {task_id}")

# Poll for status and progress
while True:
   status_response = requests.get(f"http://localhost:8000/task/{task_id}")
   status_data = status_response.json()

   progress = status_data.get("progress", 0)
   print(f"Progress: {progress*100:.1f}%", end="\r")

   if status_data["status"] == "completed":
       print("\nCompleted!")
       result = status_data["result"]
       print(f"Generated {len(result['stats']['cues'])} subtitle cues")
       print(f"SRT saved to: {result['stats']['output_path']}")
       break
   elif status_data["status"] == "failed":
       print(f"\nFailed: {status_data['error']}")
       break

   time.sleep(1)

# Cleanup task
requests.delete(f"http://localhost:8000/task/{task_id}")
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/extract-srt" \
-H "Content-Type: application/json" \
-d '{
   "video": "/path/to/video.mp4",
   "lang": "en",
   "device": "gpu:0",
   "output_path": "/path/to/output.srt"
}'
```

## Performance Benchmarks (ước tính)

| Video | Duration | Resolution | Mode | Processing Time | Speedup | Cues |
|-------|----------|------------|------|-----------------|---------|------|
| Sample 1 | 5 min | 1920x1080 | OCR (CPU) | ~45s | 1x | 150 |
| Sample 2 | 5 min | 1920x1080 | OCR (GPU) | ~20s | 2.25x | 150 |
| Sample 3 | 5 min | 1920x1080 | OCR (GPU Batch) | ~14s | **3.2x** | 150 |
| Sample 4 | 5 min | 1920x1080 | Stream | ~2s | 22.5x | 148 |
| Sample 5 | 30 min | 1280x720 | OCR (CPU) | ~4min | 1x | 900 |
| Sample 6 | 30 min | 1280x720 | OCR (GPU Batch) | ~1.5min | **2.7x** | 900 |

**Batch OCR Benefits:**
- GPU utilization: 40-60% → 80-95%
- Throughput: +30-50% faster
- Memory: Slightly higher peak usage
- Auto-enabled: When `device="gpu:*"`

*Lưu ý: Actual performance phụ thuộc hardware và video complexity*

## Troubleshooting

### OCR không chính xác
- Tăng `max_width` (trade-off: slower)
- Bật `enhance=true`
- Điều chỉnh `conf_min` threshold
- Thử các det/rec models khác

### Subtitles bị fragmented
- Tăng `merge_gap_ms`
- Giảm `sim_thr` (accept more variations)
- Tăng `debounce_frames`

### Processing quá chậm
- Giảm `target_fps`
- Tăng `hash_dist_thr` (skip more frames)
- Sử dụng `device="gpu:0"`
- Giảm `max_width`

### Memory issues
- Giảm `max_width`
- Reduce OCR cache size (sửa `_OCR_CACHE_MAX`)
- Process shorter video segments

## License & Credits

- **PaddleOCR**: Apache 2.0 License
- **OpenCV**: Apache 2.0 License
- **FastAPI**: MIT License

---

## Tài liệu bổ sung

- [LOGGING.md](LOGGING.md) - Hướng dẫn cấu hình logging và tắt debug output
- [USAGE.md](USAGE.md) - Hướng dẫn chi tiết sử dụng và examples
- [setup.py](setup.py) - Package installation setup
- [requirements.txt](requirements.txt) - Dependencies list

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

---

**Tác giả**: [Your Name]  
**Phiên bản**: 1.1.0  
**Ngày cập nhật**: February 4, 2026  
**Architecture**: Modular FastAPI + PaddleOCR v3
