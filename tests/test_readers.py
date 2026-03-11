"""Unit tests for gtin_extractor.readers module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestDecodeBarcodeReaders:
    """Tests for pyzbar and zxing reader wrappers."""

    # ------------------------------------------------------------------
    # decode_barcode_pyzbar
    # ------------------------------------------------------------------

    def test_pyzbar_returns_gtin_on_success(self):
        """pyzbar decode returning a valid GTIN should propagate it."""
        from gtin_extractor.readers import decode_barcode_pyzbar

        mock_obj = MagicMock()
        mock_obj.data = b"00012345678905"

        mock_image = MagicMock()

        with patch("gtin_extractor.readers.pyzbar_decode", return_value=[mock_obj], create=True):
            # We need to patch at the import location inside the function
            pass

        # Patch the import inside the function
        with patch.dict("sys.modules", {"pyzbar": MagicMock(), "pyzbar.pyzbar": MagicMock()}):
            import sys
            pyzbar_mock = sys.modules["pyzbar.pyzbar"]
            pyzbar_mock.decode = MagicMock(return_value=[mock_obj])
            result = decode_barcode_pyzbar(mock_image)
            assert result == "00012345678905"

    def test_pyzbar_returns_empty_when_no_barcode(self):
        """pyzbar finding no barcodes should return empty string."""
        from gtin_extractor.readers import decode_barcode_pyzbar

        mock_image = MagicMock()

        with patch.dict("sys.modules", {"pyzbar": MagicMock(), "pyzbar.pyzbar": MagicMock()}):
            import sys
            pyzbar_mock = sys.modules["pyzbar.pyzbar"]
            pyzbar_mock.decode = MagicMock(return_value=[])
            result = decode_barcode_pyzbar(mock_image)
            assert result == ""

    def test_pyzbar_handles_exception_gracefully(self):
        """Exceptions from pyzbar should be caught and return empty string."""
        from gtin_extractor.readers import decode_barcode_pyzbar

        mock_image = MagicMock()

        with patch.dict("sys.modules", {"pyzbar": MagicMock(), "pyzbar.pyzbar": MagicMock()}):
            import sys
            pyzbar_mock = sys.modules["pyzbar.pyzbar"]
            pyzbar_mock.decode = MagicMock(side_effect=RuntimeError("pyzbar fail"))
            result = decode_barcode_pyzbar(mock_image)
            assert result == ""

    # ------------------------------------------------------------------
    # decode_barcode_zxing
    # ------------------------------------------------------------------

    def test_zxing_returns_gtin_on_success(self):
        """zxing-cpp returning a valid barcode text should propagate the GTIN."""
        from gtin_extractor.readers import decode_barcode_zxing

        mock_barcode = MagicMock()
        mock_barcode.text = "00012345678905"

        mock_image = MagicMock()

        with patch.dict("sys.modules", {"zxingcpp": MagicMock()}):
            import sys
            zxing_mock = sys.modules["zxingcpp"]
            zxing_mock.read_barcodes = MagicMock(return_value=[mock_barcode])
            result = decode_barcode_zxing(mock_image)
            assert result == "00012345678905"

    def test_zxing_returns_empty_when_no_barcode(self):
        from gtin_extractor.readers import decode_barcode_zxing

        mock_image = MagicMock()
        with patch.dict("sys.modules", {"zxingcpp": MagicMock()}):
            import sys
            zxing_mock = sys.modules["zxingcpp"]
            zxing_mock.read_barcodes = MagicMock(return_value=[])
            result = decode_barcode_zxing(mock_image)
            assert result == ""

    def test_zxing_handles_exception_gracefully(self):
        from gtin_extractor.readers import decode_barcode_zxing

        mock_image = MagicMock()
        with patch.dict("sys.modules", {"zxingcpp": MagicMock()}):
            import sys
            zxing_mock = sys.modules["zxingcpp"]
            zxing_mock.read_barcodes = MagicMock(side_effect=RuntimeError("zxing fail"))
            result = decode_barcode_zxing(mock_image)
            assert result == ""


# ------------------------------------------------------------------
# process_image
# ------------------------------------------------------------------

class TestProcessImage:
    """Tests for the high-level process_image orchestration."""

    def _make_tmp_image(self, tmp_path) -> str:
        """Create a minimal 1×1 PNG image for testing."""
        from PIL import Image as PILImage

        img = PILImage.new("RGB", (1, 1), color=(255, 255, 255))
        path = tmp_path / "test.png"
        img.save(path)
        return str(path)

    def test_returns_empty_tuple_when_no_gtin_found(self, tmp_path):
        from gtin_extractor.readers import process_image

        img_path = self._make_tmp_image(tmp_path)

        with patch("gtin_extractor.readers.decode_barcode_pyzbar", return_value=""), \
             patch("gtin_extractor.readers.decode_barcode_zxing", return_value=""):
            gtin, method = process_image(img_path)

        assert gtin == ""
        assert method == ""

    def test_returns_pyzbar_result_first(self, tmp_path):
        from gtin_extractor.readers import process_image

        img_path = self._make_tmp_image(tmp_path)

        with patch("gtin_extractor.readers.decode_barcode_pyzbar", return_value="00012345678905"), \
             patch("gtin_extractor.readers.decode_barcode_zxing", return_value="") as mock_zxing:
            gtin, method = process_image(img_path)

        assert gtin == "00012345678905"
        assert method == "pyzbar"
        mock_zxing.assert_not_called()

    def test_falls_back_to_zxing(self, tmp_path):
        from gtin_extractor.readers import process_image

        img_path = self._make_tmp_image(tmp_path)

        with patch("gtin_extractor.readers.decode_barcode_pyzbar", return_value=""), \
             patch("gtin_extractor.readers.decode_barcode_zxing", return_value="00012345678905"):
            gtin, method = process_image(img_path)

        assert gtin == "00012345678905"
        assert method == "zxing"

    def test_falls_back_to_gemini_when_key_provided(self, tmp_path):
        from gtin_extractor.readers import process_image

        img_path = self._make_tmp_image(tmp_path)

        with patch("gtin_extractor.readers.decode_barcode_pyzbar", return_value=""), \
             patch("gtin_extractor.readers.decode_barcode_zxing", return_value=""), \
             patch("gtin_extractor.gemini_integration.decode_barcode_gemini",
                   return_value="00012345678905"):
            gtin, method = process_image(img_path, gemini_key="fake-key")

        assert gtin == "00012345678905"
        assert method == "gemini"

    def test_handles_corrupt_image_gracefully(self, tmp_path):
        from gtin_extractor.readers import process_image

        bad_path = tmp_path / "bad.png"
        bad_path.write_bytes(b"not an image")

        gtin, method = process_image(str(bad_path))
        assert gtin == ""
        assert method == ""
