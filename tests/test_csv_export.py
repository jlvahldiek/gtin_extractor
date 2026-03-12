"""Unit tests for gtin_extractor.csv_export module."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from gtin_extractor.csv_export import FIELDNAMES, CSVWriter, build_row, deduplicate_rows, write_results_csv


class TestBuildRow:
    """Tests for the build_row helper."""

    def test_builds_row_with_gtin(self):
        row = build_row("img.png", "00012345678905", "pyzbar", {})
        assert row["filename"] == "img.png"
        assert row["gtin"] == "00012345678905"
        assert row["gtin_detection_status"] == "validated"
        assert row["gtin_detection_method"] == "pyzbar"

    def test_builds_row_without_gtin(self):
        row = build_row("img.png", "", "", {})
        assert row["gtin"] == ""
        assert row["gtin_detection_status"] == "invalid"
        assert row["gtin_detection_method"] == ""

    def test_product_info_fields_populated(self):
        info = {
            "manufacturer": "Medline",
            "ref": "DYND74155",
            "ref_confidence": "high",
            "product_name": "Gloves",
            "product_specs": "Size 7.5; Latex",
        }
        row = build_row("img.png", "00012345678905", "zxing", info)
        assert row["manufacturer"] == "Medline"
        assert row["ref"] == "DYND74155"
        assert row["ref_confidence"] == "high"
        assert row["product_name"] == "Gloves"
        assert row["product_specs"] == "Size 7.5; Latex"

    def test_missing_product_info_defaults_to_empty(self):
        row = build_row("img.png", "", "", {})
        assert row["manufacturer"] == ""
        assert row["ref"] == ""
        assert row["ref_confidence"] == ""
        assert row["product_name"] == ""
        assert row["product_specs"] == ""

    def test_row_has_all_fieldnames(self):
        row = build_row("img.png", "", "", {})
        assert set(row.keys()) == set(FIELDNAMES)


class TestCSVWriter:
    """Tests for the CSVWriter context manager."""

    def test_creates_csv_file(self, tmp_path):
        csv_path = tmp_path / "out.csv"
        row = build_row("img.png", "00012345678905", "pyzbar", {})
        with CSVWriter(csv_path) as writer:
            writer.writerow(row)
        assert csv_path.exists()

    def test_csv_has_header(self, tmp_path):
        csv_path = tmp_path / "out.csv"
        with CSVWriter(csv_path):
            pass  # No rows – just header
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == FIELDNAMES

    def test_csv_row_written_correctly(self, tmp_path):
        csv_path = tmp_path / "out.csv"
        row = build_row("img.png", "00012345678905", "gemini", {"manufacturer": "ACME"})
        with CSVWriter(csv_path) as writer:
            writer.writerow(row)
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 1
        assert rows[0]["gtin"] == "00012345678905"
        assert rows[0]["manufacturer"] == "ACME"

    def test_writerow_outside_context_raises(self, tmp_path):
        writer = CSVWriter(tmp_path / "out.csv")
        with pytest.raises(RuntimeError):
            writer.writerow({})

    def test_multiple_rows(self, tmp_path):
        csv_path = tmp_path / "out.csv"
        rows_in = [build_row(f"img{i}.png", "", "", {}) for i in range(5)]
        with CSVWriter(csv_path) as writer:
            for row in rows_in:
                writer.writerow(row)
        with open(csv_path, newline="", encoding="utf-8") as fh:
            rows_out = list(csv.DictReader(fh))
        assert len(rows_out) == 5


class TestWriteResultsCsv:
    """Tests for the write_results_csv convenience function."""

    def test_writes_all_rows(self, tmp_path):
        csv_path = tmp_path / "results.csv"
        rows = [build_row(f"img{i}.png", "", "", {}) for i in range(3)]
        write_results_csv(iter(rows), csv_path)
        with open(csv_path, newline="", encoding="utf-8") as fh:
            out = list(csv.DictReader(fh))
        assert len(out) == 3

    def test_accepts_path_object(self, tmp_path):
        csv_path = tmp_path / "results.csv"
        write_results_csv([], Path(csv_path))
        assert csv_path.exists()


class TestDeduplicateRows:
    """Tests for the deduplicate_rows helper."""

    def test_removes_duplicate_gtins(self):
        rows = [
            build_row("img1.png", "00012345678905", "pyzbar", {}),
            build_row("img2.png", "00012345678905", "zxing", {}),
        ]
        result = deduplicate_rows(rows)
        assert len(result) == 1
        assert result[0]["filename"] == "img1.png"

    def test_keeps_distinct_gtins(self):
        rows = [
            build_row("img1.png", "00012345678905", "pyzbar", {}),
            build_row("img2.png", "5901234123457", "pyzbar", {}),
        ]
        result = deduplicate_rows(rows)
        assert len(result) == 2

    def test_keeps_all_empty_gtin_rows(self):
        rows = [
            build_row("img1.png", "", "", {}),
            build_row("img2.png", "", "", {}),
        ]
        result = deduplicate_rows(rows)
        assert len(result) == 2

    def test_empty_input_returns_empty(self):
        assert deduplicate_rows([]) == []

    def test_no_duplicates_unchanged(self):
        rows = [
            build_row("img1.png", "00012345678905", "pyzbar", {}),
            build_row("img2.png", "5901234123457", "zxing", {}),
            build_row("img3.png", "", "", {}),
        ]
        result = deduplicate_rows(rows)
        assert len(result) == 3

    def test_preserves_order_of_first_occurrence(self):
        rows = [
            build_row("a.png", "00012345678905", "pyzbar", {}),
            build_row("b.png", "5901234123457", "pyzbar", {}),
            build_row("c.png", "00012345678905", "gemini", {}),
        ]
        result = deduplicate_rows(rows)
        assert len(result) == 2
        assert result[0]["filename"] == "a.png"
        assert result[1]["filename"] == "b.png"
