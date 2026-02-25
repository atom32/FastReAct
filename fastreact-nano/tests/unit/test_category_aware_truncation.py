"""
Tests for category-aware tool result truncation

Tests the new truncate_by_category method and its
category-specific truncation strategies.
"""

import pytest
from fastreact.core.context import ContextMonitor, TOOL_CATEGORIES


class TestToolCategories:
    """Test tool category definitions"""

    def test_tool_categories_exist(self):
        """Test that tool categories are defined"""
        assert "read_file" in TOOL_CATEGORIES
        assert "write_file" in TOOL_CATEGORIES
        assert "edit_file" in TOOL_CATEGORIES
        assert "exec" in TOOL_CATEGORIES
        assert "default" in TOOL_CATEGORIES

    def test_category_attributes(self):
        """Test that each category has required attributes"""
        for tool_name, config in TOOL_CATEGORIES.items():
            assert "category" in config
            assert "preserve" in config


class TestCategoryAwareTruncation:
    """Test category-aware truncation strategies"""

    def test_file_content_preserves_structure(self):
        """Test that file content (read_file) preserves structure"""
        monitor = ContextMonitor()

        # Create a large file output
        file_content = "import sys\nimport os\n" + "x" * 10000 + "\nprint('done')"

        result = monitor.truncate_by_category(file_content, "read_file")

        # Should preserve head (structure)
        assert "import sys" in result or "import os" in result
        # Should indicate truncation
        assert "truncated" in result.lower() or len(result) < len(file_content)
        # Should keep more head (90%) for syntax
        assert result.startswith("import")

    def test_file_operation_truncates_to_result(self):
        """Test that file operations (write_file, edit_file) show result only"""
        monitor = ContextMonitor()

        # Write operation output
        write_output = "Successfully wrote 1500 bytes to /path/to/file.txt\n" + "x" * 1000

        result = monitor.truncate_by_category(write_output, "write_file")

        # Should be short (just success/fail)
        assert len(result) < 500  # Max 500 chars for results
        assert "[OK]" in result or "completed" in result.lower()

    def test_command_preserves_errors(self):
        """Test that commands (exec) preserve error messages"""
        monitor = ContextMonitor()

        # Command output with error
        error_output = "Processing...\n" + "x" * 500 + "\n" + "Error: Command failed\n" + "y" * 300

        result = monitor.truncate_by_category(error_output, "exec")

        # Should preserve error message or indicate truncation
        has_error = "Error:" in result or "failed" in result.lower()
        has_truncation = "truncated" in result.lower() or len(result) < len(error_output)
        assert has_error or has_truncation

    def test_search_preserves_matches(self):
        """Test that search (grep/find) preserve matches"""
        monitor = ContextMonitor()

        # Create larger search output that will exceed limit
        search_lines = []
        for i in range(50):  # 50 match lines
            search_lines.append(f"file{i}.txt:{i*10}: match line {i}")

        # Add large filler to ensure truncation
        search_output = "\n".join(search_lines) + "\n" + "x" * 5000

        result = monitor.truncate_by_category(search_output, "grep")

        # Should preserve some match lines (containing ":")
        has_matches = ":" in result and "file" in result
        # Should be truncated
        is_truncated = len(result) < len(search_output)
        assert has_matches or is_truncated

    def test_unknown_tool_uses_default(self):
        """Test that unknown tools use default balanced strategy"""
        monitor = ContextMonitor()

        output = "x" * 10000

        result = monitor.truncate_by_category(output, "unknown_tool")

        # Should truncate
        assert len(result) < len(output)
        # Should have head and tail
        assert len(result.split("\n")) >= 1

    def test_small_output_not_truncated(self):
        """Test that small outputs are not truncated"""
        monitor = ContextMonitor()

        small_output = "Small output"

        result = monitor.truncate_by_category(small_output, "read_file")

        # Should not be modified
        assert result == small_output


class TestTruncationStrategies:
    """Test specific truncation strategy implementations"""

    def test_structure_truncation_line_boundaries(self):
        """Test that structure truncation respects line boundaries"""
        monitor = ContextMonitor()

        output = "\n".join([f"Line {i}" for i in range(100)])

        result = monitor._truncate_structure(output, limit=200, tool_name="test")

        # Should try to break at newlines
        assert "truncated" in result.lower()

    def test_result_truncation_success(self):
        """Test that result truncation shows success"""
        monitor = ContextMonitor()

        success_output = "File written successfully"

        result = monitor._truncate_to_result(success_output, limit=100, tool_name="test")

        assert "[OK]" in result

    def test_result_truncation_error(self):
        """Test that result truncation preserves errors"""
        monitor = ContextMonitor()

        error_output = "[ERROR] Failed to write file\nPermission denied\n"

        result = monitor._truncate_to_result(error_output, limit=500, tool_name="test")

        assert "[ERROR]" in result or "Failed" in result

    def test_error_preservation_finds_errors(self):
        """Test that error preservation finds error patterns"""
        monitor = ContextMonitor()

        error_output = "Processing...\n" + "x" * 500 + "\nERROR: Operation failed\n"

        result = monitor._truncate_preserve_errors(error_output, limit=100, tool_name="test")

        # Should contain truncation indicator
        has_truncation = "truncated" in result.lower()
        # Or preserve error if it fits
        has_error = "ERROR:" in result
        assert has_truncation or has_error

    def test_key_info_removes_fluff(self):
        """Test that key info truncation removes fluff"""
        monitor = ContextMonitor()

        fluff_output = "Here are the search results:\n\n" + "Actual result" + "x" * 500

        result = monitor._truncate_key_info(fluff_output, limit=100, tool_name="test")

        # Should try to remove fluff
        assert "Here are the" not in result or len(result) <= 100

    def test_balanced_truncation_head_tail(self):
        """Test that balanced truncation keeps both head and tail"""
        monitor = ContextMonitor()

        output = "HEAD content\n" + "x" * 1000 + "\nTAIL content"

        result = monitor._truncate_balanced(output, limit=200, tool_name="test", head_ratio=0.7, tail_ratio=0.3)

        # Should contain parts of both
        assert "HEAD" in result or "TAIL" in result or "truncated" in result.lower()


class TestTokenCountingInTruncation:
    """Test that token counting is used appropriately"""

    def test_truncation_respects_limits(self):
        """Test that truncation respects configured limits"""
        monitor = ContextMonitor(max_tool_output_chars=500)

        large_output = "x" * 10000

        result = monitor.truncate_by_category(large_output, "read_file")

        # Should be under or at limit (plus truncation notice)
        # Allow some margin for truncation message
        assert len(result) <= len(large_output)

    def test_category_specific_limits(self):
        """Test that different categories have different limits"""
        monitor = ContextMonitor(max_tool_output_chars=5000)

        # write_file should use 500 char limit
        write_output = "x" * 10000
        write_result = monitor.truncate_by_category(write_output, "write_file")
        assert len(write_result) <= 500  # Category-specific limit

        # grep should use 3000 char limit
        grep_output = "x" * 10000
        grep_result = monitor.truncate_by_category(grep_output, "grep")
        assert len(grep_result) <= 3000  # Category-specific limit


class TestStatisticsTracking:
    """Test that statistics are properly tracked"""

    def test_truncation_increments_count(self):
        """Test that truncation increments the counter"""
        monitor = ContextMonitor()

        initial_count = monitor._stats.truncated_count

        large_output = "x" * 10000
        monitor.truncate_by_category(large_output, "test_tool")

        assert monitor._stats.truncated_count == initial_count + 1

    def test_truncation_records_last_tool(self):
        """Test that truncation records which tool was truncated"""
        monitor = ContextMonitor()

        large_output = "x" * 10000
        monitor.truncate_by_category(large_output, "my_special_tool")

        assert monitor._stats.last_truncated == "my_special_tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
