# MIDI Processing

A lightweight MIDI parsing and music theory analysis toolkit for Python.

## Overview

MIDI Processing is a modular library designed for parsing MIDI files and performing music theory analysis. It provides tools for:

- **MIDI Parsing**: Parse multi-track Standard MIDI Files (SMF) with tempo changes
- **Track Mapping**: Automatically categorize tracks based on names or instrument programs
- **Music Analysis**: Detect keys, identify chords, and analyze rhythm patterns
- **Timeline Generation**: Quantize and align musical events

## Features

- ✓ Multi-track MIDI support with tempo change handling
- ✓ Accurate tick-to-seconds conversion
- ✓ Configurable track-to-role mapping using regex patterns
- ✓ Key detection using Krumhansl-Schmuckler algorithm
- ✓ Window-based chord recognition (major, minor, diminished)
- ✓ Rhythm pattern analysis via inter-onset intervals
- ✓ Note quantization and overlap handling
- ✓ Comprehensive test coverage with pytest

## Installation

### Using pip (recommended)

```bash
pip install -r requirements.txt
```

### Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Install dependencies:
```bash
pip install mido>=1.2.10 pytest>=6.0.0
```

For YAML configuration support, also install:
```bash
pip install pyyaml
```

## Quick Start

### Basic Usage

```python
from midi_processing import parse_midi, detect_key, analyze_chords

# Parse a MIDI file
events = parse_midi('example.mid')

# Detect the musical key
key = detect_key(events)
print(f"Detected key: {key}")

# Analyze chords
chords = analyze_chords(events, window=0.5)
for chord in chords[:5]:
    print(f"Time {chord['time']:.2f}s: {chord['root']} {chord['type']}")
```

### Advanced Parsing

```python
from midi_processing import AdvancedMIDIParser

parser = AdvancedMIDIParser()

# Parse MIDI file
events = parser.parse_midi_file('song.mid')

# Detect tracks and metadata
tracks = parser.detect_tracks('song.mid')
for track in tracks:
    print(f"Track {track['track_id']}: {track['track_name']} (Programs: {track['programs']})")
```

### Track Mapping

```python
from midi_processing import TrackMapper

# Use default mapping rules
mapper = TrackMapper()
track_names = ['Piano Left', 'Piano Right', 'Bass Guitar', 'Drum Kit']
mapping = mapper.auto_map_tracks(track_names=track_names)
print(mapping)  # {'Piano Left': 'piano', 'Piano Right': 'piano', 'Bass Guitar': 'bass', 'Drum Kit': 'drums'}

# Use custom YAML configuration
mapper = TrackMapper(config_path='config/mapping_rules.yaml')
mapping = mapper.auto_map_tracks(events=events)

# Create custom mapping rules
custom_rules = {
    r'.*synth.*': 'synthesizer',
    r'.*vocal.*': 'vocals'
}
mapper.create_custom_mapping(custom_rules)
```

### Rhythm and Timeline Analysis

```python
from midi_processing import rhythm_pattern, MusicTimeline

# Analyze rhythm patterns (top 5 most common inter-onset intervals)
patterns = rhythm_pattern(events, top_k=5)
for interval, count in patterns:
    print(f"Interval: {interval}s, Count: {count}")

# Quantize and align notes
timeline = MusicTimeline(quantize=0.125)  # 32nd note quantization
aligned_events = timeline.align_notes(events)
```

## Project Structure

```
midi_processing/
├── __init__.py              # Package initialization and exports
├── midi_parser.py           # MIDI file parsing with tempo handling
├── track_mapper.py          # Track name to role mapping
├── music_analyzer.py        # Key detection, chord and rhythm analysis
├── timeline_generator.py    # Note quantization and timeline generation
├── test_cases/
│   └── test_midi_processing.py  # Unit tests
└── README.md                # This file (Chinese version)

config/
├── mapping_rules.yaml       # Track mapping configuration
└── analysis_config.yaml     # Analysis parameters

docs/
├── API.md                   # Detailed API reference
├── CONFIGURATION.md         # Configuration file documentation
└── EXAMPLES.md              # Usage examples and code samples
```

## Configuration

### Mapping Rules (`config/mapping_rules.yaml`)

Define regex patterns to map track names to musical roles:

```yaml
'.*vocal.*|.*voice.*': vocals
'.*melody.*|.*lead.*': melody
'.*bass.*': bass
'.*drum.*|.*percussion.*': drums
'.*chord.*|.*pad.*': harmony
'piano|grand': piano
```

### Analysis Configuration (`config/analysis_config.yaml`)

Adjust analysis parameters:

```yaml
chord_window: 0.5      # Window size (seconds) for chord detection
quantize: 0.125        # Quantization grid (seconds) - 0.125 = 32nd note at 120bpm
rhythm_top_k: 5        # Number of top rhythm patterns to return
```

## API Overview

### Core Functions

- `parse_midi(path: str) -> List[Dict]` - Parse MIDI file and return note events
- `detect_key(events: List[Dict]) -> str` - Detect musical key (e.g., "C major")
- `analyze_chords(events: List[Dict], window: float) -> List[Dict]` - Identify chords in time windows
- `rhythm_pattern(events: List[Dict], top_k: int) -> List[Tuple]` - Extract common rhythm patterns
- `align_notes(events: List[Dict], quantize: float) -> List[Dict]` - Quantize note timings
- `map_tracks(track_names: List[str], rules: Optional[List[Tuple]]) -> Dict` - Map track names to roles

### Classes

- `AdvancedMIDIParser` - High-level parser with track detection
- `TrackMapper` - Configurable track-to-role mapping
- `MusicTimeline` - Timeline generation and note alignment

For detailed API documentation, see [docs/API.md](docs/API.md).

## Running Tests

The project includes comprehensive unit tests using pytest:

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run quietly
pytest -q

# Run specific test file
pytest midi_processing/test_cases/test_midi_processing.py
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'mido'`
- **Solution**: Install dependencies with `pip install mido`

**Issue**: MIDI file parsing returns empty events list
- **Solution**: Ensure the MIDI file contains note events (not just meta-events or control changes)

**Issue**: Key detection returns "Unknown"
- **Solution**: The MIDI file may have too few notes or an ambiguous key signature. Try with a longer musical phrase.

**Issue**: Chord detection returns mostly "cluster" types
- **Solution**: Adjust the `window` parameter in `analyze_chords()`. Try larger values (e.g., 1.0) for slower music.

**Issue**: YAML configuration not loading
- **Solution**: Install PyYAML with `pip install pyyaml`

### Getting Help

For bugs or feature requests, please open an issue on the project repository.

## Architecture

The library follows a modular design pattern:

1. **Parser Layer** (`midi_parser.py`): Low-level MIDI file parsing, tempo map construction, and tick-to-time conversion
2. **Mapping Layer** (`track_mapper.py`): Flexible track categorization using configurable regex rules
3. **Analysis Layer** (`music_analyzer.py`): Music theory algorithms (key detection, chord recognition, rhythm analysis)
4. **Timeline Layer** (`timeline_generator.py`): Event quantization and timeline sequence generation

This separation allows users to use individual components independently or combine them for complex workflows.

## License

[Add license information here]

## Contributing

Contributions are welcome! Please ensure all tests pass before submitting pull requests.

## Acknowledgments

- Key detection uses the Krumhansl-Schmuckler key-finding algorithm
- MIDI parsing powered by [mido](https://github.com/mido/mido)
Agent 1: 音源分离与清洗专家

任务编号: A1
依赖: 原始音频数据
prompt

你是一个专业的音频工程师，负责将原始哈基米音频分离为干净的人声轨道。

**核心任务**：
1. 使用UVR5进行高质量音源分离
   - 分离人声(vocals)和伴奏(accompaniment)
   - 确保人声轨道无音乐残留
   - 保持原始音质不受损

2. 音频清洗与预处理
   - 降噪处理，提高信噪比
   - 电平标准化(-23 LUFS)
   - 切除静音段落
   - 修复音频缺陷

**输出要求**：
- 分离后的WAV文件(44.1kHz, 16bit)
- 质量检测报告
- 文件结构：

cleaned_audio/
├── vocals/ # 纯人声
├── accompaniment/ # 伴奏
└── quality_report.json
text


**验收标准**：
- 人声纯净度 > 95%
- 信噪比 > 30dB
- 无明显的音频伪影

**预计时间**: 48小时

Agent 2: 语素自动发现与切割专家

任务编号: A2
依赖: A1的输出（清洗后人声音频）
prompt

你是一个语音学与模式识别专家，负责自动发现哈基米音频中的语素单元。

**核心任务**：
1. 自动音频分段
   - 基于声学变化检测边界
   - 结合语义和韵律特征
   - 生成初步音频片段

2. 语素发现与聚类
   - 使用DTW发现重复模式
   - 多层次聚类分析
   - 识别50-200个独特语素

3. 智能分类与标注
   - 建立语素分类体系：
     * 哈基米变体
     * 动物叫声
     * 情感感叹
     * 节奏元素
     * 旋律短语
     * 拟声词
   - 自动生成描述性标签

4. 质量评估
   - 评估语素清晰度
   - 计算独特性得分
   - 筛选高质量语素

**输出要求**：
- 结构化语素库(150+语素)
- 语素元数据数据库
- 发现过程分析报告
- 文件结构：

morpheme_library/
├── raw_morphemes/
├── categorized/
├── morpheme_database.json
└── discovery_report.pdf
text


**验收标准**：
- 发现语素数量: 50-200个
- 平均质量得分 > 0.7
- 类别分布均衡
- 边界切割自然

**预计时间**: 60小时

Agent 3: 音色分析与特征工程专家

任务编号: A3
依赖: A2的输出（语素库）
prompt

你是一个音频信号处理与机器学习专家，负责深度音色分析和特征提取。

**核心任务**：
1. 多层次特征提取
   - 传统特征: MFCC, 色度, 频谱质心, 过零率
   - 深度特征: VGGish, PANNs嵌入
   - 音乐特征: 音高轮廓, 谐波结构, 节奏特征

2. 音色特性分析
   - 旋律性vs节奏性分类
   - 音色相似度矩阵
   - 音色空间可视化

3. 稳定性分析
   - 识别稳定音频段
   - 计算稳定度评分
   - 标记稳定核心时间戳

4. 特征优化
   - 特征选择与降维
   - 特征标准化
   - 构建特征索引

**输出要求**：
- 完整的特征数据集
- 音色分析报告
- 特征可视化图表
- 文件结构：

feature_analysis/
├── feature_vectors.npy
├── timbre_analysis.json
├── stability_scores.csv
└── visualizations/
text


**验收标准**：
- 特征提取完整率100%
- 分类准确率 > 90%
- 特征区分度明显
- 可视化清晰易懂

**预计时间**: 48小时


