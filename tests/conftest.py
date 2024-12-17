"""PyTest configuration and fixtures."""
import os
import pytest
from pathlib import Path


@pytest.fixture
def template_dir(tmp_path):
    """Create a temporary directory for template files."""
    return tmp_path


@pytest.fixture
def template_file(template_dir):
    """Create a sample template file."""
    template_content = """
    <html>
        <head>
            <title>{{ title }}</title>
        </head>
        <body>
            <h1>{{ heading }}</h1>
            @if(show_content)
                <p>{{ content }}</p>
            @endif
            
            @for(item in items)
                <li>{{ item }}</li>
            @endfor
        </body>
    </html>
    """
    file_path = template_dir / "test.html"
    file_path.write_text(template_content)
    return file_path


@pytest.fixture
def component_file(template_dir):
    """Create a sample component file."""
    component_content = """
    @props({
        'title': 'Default Title',
        'show_footer': True
    })
    <div class="component">
        <h2>{{ title }}</h2>
        {{ slot }}
        @if(show_footer)
            <footer>Component Footer</footer>
        @endif
    </div>
    """
    file_path = template_dir / "components" / "test-component.html"
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text(component_content)
    return file_path


@pytest.fixture
def mock_request():
    """Create a mock request object for testing."""
    class MockUser:
        is_authenticated = True
        
    class MockRequest:
        def __init__(self):
            self.user = MockUser()
            self.path_info = "/test/"
            
    return MockRequest()
