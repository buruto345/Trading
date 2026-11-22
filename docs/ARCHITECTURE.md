# Kiến trúc

`data_collection` tải HTTPS công khai, cache ZIP/checksum; `data_validation` kiểm tra và Parquet.
`pattern_detection` state machine tuần tự, swing/sweep/FVG/MSS và rejected observations.
`simulation` next-open, stop/target, M1 ambiguity, censor và risk-unit outcomes.
`statistics` metric, Wilson, bootstrap, subgroup/FDR, cost sensitivity.
`visualization` chuẩn bị chart và case study; `reporting` Jinja2 + Plotly JavaScript nhúng.
`scripts/run_pipeline.py` điều phối, checkpoints và log; `tests` unit/integration; browser QA riêng.

Timestamp chuẩn UTC. M5 timestamp là open, confirmation_time là close boundary. Mọi nguồn giá dùng timestamp có sẵn tại thời điểm tương ứng. Parquet chứa quan sát gốc để đối chiếu, JSON là bản tổng hợp, HTML không có nguồn giá riêng.
Tách module đủ kiểm thử; không microservice, ML hay kết nối đặt lệnh.

