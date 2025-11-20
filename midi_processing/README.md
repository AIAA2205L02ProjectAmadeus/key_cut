# midi_processing

轻量级 MIDI 解析与简单乐理分析工具。

结构：

midi_processing/
- midi_parser.py  # MIDI 解析
- track_mapper.py # 轨道映射规则
- music_analyzer.py # 调性/和弦/节奏分析
- timeline_generator.py # 时间线生成
- analysis_result.py # 分析结果数据类
- exporter.py # 导出功能（JSON/CSV/YAML/文本）
- cli.py # 命令行工具
- test_cases/test_midi_processing.py # pytest 测试

快速开始：

1. 安装依赖：

   pip install -r requirements.txt

2. 运行测试：

   pytest -q

接口示例（Python）：

from midi_processing import midi_parser, music_analyzer
events = midi_parser.parse_midi('example.mid')
print(music_analyzer.detect_key(events))

导出分析结果：

from midi_processing import (
    parse_midi, detect_key, analyze_chords,
    rhythm_pattern, map_tracks_from_parser_events,
    MusicTimeline, AnalysisResult, export_analysis
)

# 完整分析流程
notes = parse_midi('example.mid')
key = detect_key(notes)
chords = analyze_chords(notes)
rhythm = rhythm_pattern(notes)
tracks = map_tracks_from_parser_events(notes)
timeline = MusicTimeline().align_notes(notes)

# 创建结果对象并导出
result = AnalysisResult(
    notes=notes, key=key, chords=chords,
    rhythm_patterns=rhythm, track_mapping=tracks,
    timeline=timeline
)
export_analysis(result, 'output.json', format='json')

命令行工具：

python -m midi_processing.cli input.mid --output-format json --output-file results.json

支持格式：json, csv, yaml, txt
详情级别：summary, detailed, full

更多文档请参考 examples/EXPORT_DOCUMENTATION.md
