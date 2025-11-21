from src.shared.device import _log_unsupported_gpus


def test_log_unsupported_gpu_warns_for_low_capability(caplog) -> None:
    class FakeCuda:
        def device_count(self) -> int:
            return 2

        def get_device_capability(self, index: int) -> tuple[int, int]:
            return (8, 0) if index == 0 else (6, 1)

        def get_device_name(self, index: int) -> str:
            return f"GPU{index}"

    class FakeTorch:
        cuda: FakeCuda = FakeCuda()

    caplog.set_level("WARNING")
    _log_unsupported_gpus(FakeTorch())

    assert any("device_unsupported_gpu_detected" in record.message for record in caplog.records)
