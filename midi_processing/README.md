# midi_processing

轻量级 MIDI 解析与简单乐理分析工具。

结构：

midi_processing/
- midi_parser.py  # MIDI 解析
- track_mapper.py # 轨道映射规则
- music_analyzer.py # 调性/和弦/节奏分析
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
