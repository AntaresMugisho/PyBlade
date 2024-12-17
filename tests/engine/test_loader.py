"""Tests for the template loader."""
import pytest
from pathlib import Path
from pyblade.engine.loader import TemplateLoader
from pyblade.engine.exceptions import TemplateNotFoundError


def test_load_template(template_dir, template_file):
    """Test loading a template from a file."""
    loader = TemplateLoader([template_dir])
    template = loader.load_template("test.html")
    
    assert template is not None
    assert template.source == template_file.read_text()


def test_load_template_from_multiple_dirs(tmp_path):
    """Test loading templates from multiple directories."""
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()
    
    # Create template in second directory
    template_path = dir2 / "test.html"
    template_path.write_text("Template content")
    
    loader = TemplateLoader([dir1, dir2])
    template = loader.load_template("test.html")
    
    assert template is not None
    assert template.source == "Template content"


def test_load_nonexistent_template(template_dir):
    """Test that loading a nonexistent template raises an error."""
    loader = TemplateLoader([template_dir])
    
    with pytest.raises(TemplateNotFoundError):
        loader.load_template("nonexistent.html")


def test_load_template_with_extension(template_dir, template_file):
    """Test loading a template with different extensions."""
    loader = TemplateLoader([template_dir])
    
    # Should find template with .html extension
    template = loader.load_template("test")
    assert template is not None
    
    # Should also find template with explicit extension
    template = loader.load_template("test.html")
    assert template is not None


def test_load_template_from_subdirectory(template_dir):
    """Test loading a template from a subdirectory."""
    subdir = template_dir / "subdir"
    subdir.mkdir()
    
    template_path = subdir / "test.html"
    template_path.write_text("Subdir template")
    
    loader = TemplateLoader([template_dir])
    template = loader.load_template("subdir/test.html")
    
    assert template is not None
    assert template.source == "Subdir template"


def test_template_cache(template_dir, template_file):
    """Test that templates are properly cached."""
    loader = TemplateLoader([template_dir])
    
    # First load should cache the template
    template1 = loader.load_template("test.html")
    
    # Modify the file (shouldn't affect cached template)
    template_file.write_text("Modified content")
    
    # Second load should return cached template
    template2 = loader.load_template("test.html")
    
    assert template1.source == template2.source


def test_clear_cache(template_dir, template_file):
    """Test clearing the template cache."""
    loader = TemplateLoader([template_dir])
    
    # Load and cache template
    template1 = loader.load_template("test.html")
    
    # Modify file and clear cache
    template_file.write_text("Modified content")
    loader.clear_cache()
    
    # Load template again - should get modified content
    template2 = loader.load_template("test.html")
    
    assert template1.source != template2.source
    assert template2.source == "Modified content"
