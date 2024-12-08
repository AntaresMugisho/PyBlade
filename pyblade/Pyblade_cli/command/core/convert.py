
import re
def convert_django_to_pyblade(content):
    """
    Converts Django templates to PyBlade syntax while ignoring comments.
    This function replaces Django-specific syntax with PyBlade syntax.

    Parameters:
        content (str): The content of the Django template to be converted.

    Returns:
        str: The converted PyBlade content.
    """
    
    # Extract all comments from the content for later restoration
    extracted_comments = re.findall(r'{#.*?#}', content, flags=re.DOTALL)  
    content_without_comments = re.sub(r'{#.*?#}', '{#COMMENT#}', content, flags=re.DOTALL)  

    # Convert Django's {% extends %} syntax to PyBlade's @extends syntax
    content_without_comments = re.sub(r'{%\s*extends\s+"(.*?)\.html"\s*%}', r'@extends("\1")', content_without_comments)

    # Convert Django's {% block %} syntax to PyBlade's @yield and @block syntax
    if '@extends' not in content_without_comments:
        content_without_comments = re.sub(r'{%\s*block\s+(.*?)\s*%}', r'@yield("\1")', content_without_comments)
        content_without_comments = re.sub(r'{%\s*endblock\s+(.*?)\s*%}', '', content_without_comments)  
    else:
        content_without_comments = re.sub(r'{%\s*block\s+(.*?)\s*%}(.*?){%\s*endblock\s*%}', 
                                          lambda match: f"@block('{match.group(1)}')\n{match.group(2)}@endblock", 
                                          content_without_comments, flags=re.DOTALL)
    
    # Further conversion of Django template blocks to PyBlade syntax
    content_without_comments = re.sub(r'{%\s*block\s+(.*?)\s*%}(.*?){%\s*endblock\s*%}', 
                                      lambda match: f"@block {match.group(1)}\n{match.group(2)}@endblock", 
                                      content_without_comments, flags=re.DOTALL)

    # Convert Django's {% include %} and {% if %} syntax to PyBlade's @include and @if syntax
    content_without_comments = re.sub(r'{%\s*include\s+"(.*?)"\s*%}', r'@include("\1")', content_without_comments)
    content_without_comments = re.sub(r'{%\s*if\s+(.*?)\s*%}', r'@if(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*elif\s+(.*?)\s*%}', r'@elseif(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*else\s*%}', r'@else', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endif\s*%}', r'@endif', content_without_comments)
    content_without_comments = re.sub(r'{%\s*for\s+(.*?)\s+in\s+(.*?)\s*%}', r'@for(\1 : \2)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endfor\s*%}', r'@endfor', content_without_comments)
    
    # Ensure proper spacing around variables in the {{ }} syntax
    content_without_comments = re.sub(r'{{\s*(.*?)\s*}}', r'{{ \1 }}', content_without_comments)

    # Convert Django's {% trans %} syntax to PyBlade's @trans syntax
    content_without_comments = re.sub(r'{%\s*trans\s+"(.*?)"\s*%}', r'@trans("\1")', content_without_comments)
    content_without_comments = re.sub(r'{%\s*trans\s+(.*?)\s*%}', r'@trans(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*translate\s+"(.*?)"\s*%}', r'@translate("\1")', content_without_comments)
    content_without_comments = re.sub(r'{%\s*translate\s+(.*?)\s*%}', r'@translate(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*localize\s+(on|off)\s*%}', r'@localize("\1")', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endlocalize\s+(.*?)\s*%}', r'@endlocalize', content_without_comments)
    content_without_comments = re.sub(r'{%\s*csrf_token\s+(.*?)\s*%}', r'@csrf_token', content_without_comments)
    content_without_comments = re.sub(r'{%\s*ifchanged\s*%}', r'@ifchanged', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endifchanged\s*%}', r'@endifchanged', content_without_comments)
    content_without_comments = re.sub(r'{%\s*with\s+(.*?)\s*%}', r'@with(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endwith\s*%}', r'@endwith', content_without_comments)
    content_without_comments = re.sub(r'{%\s*autoescape\s+(.*?)\s*%}', r'@autoescape(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endautoescape\s*%}', r'@endautoescape', content_without_comments)
    content_without_comments = re.sub(r'{%\s*verbatim\s*%}', r'@verbatim', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endverbatim\s*%}', r'@endverbatim', content_without_comments)
    content_without_comments = re.sub(r'{%\s*spaceless\s*%}', r'@spaceless', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endspaceless\s*%}', r'@endspaceless', content_without_comments)
    content_without_comments = re.sub(r'{%\s*comment\s*%}', r'@comment', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endcomment\s*%}', r'@endcomment', content_without_comments)
    content_without_comments = re.sub(r'{%\s*cache\s+(.*?)\s*%}', r'@cache(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*endcache\s*%}', r'@endcache', content_without_comments)
    content_without_comments = re.sub(r'{%\s*empty\s+(.*?)\s*%}', r'@empty(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*now\s+(.*?)\s*%}', r'@now(\1)', content_without_comments)
    content_without_comments = re.sub(r'{%\s*static\s+(.*?)\s*%}', r'@static(\1)', content_without_comments)
    
    
    
    content_without_comments = re.sub(r'{%\s*load\s+"(.*?)"\s*%}', '', content_without_comments)
   
    # Handle URL tag conversion
    content_without_comments = re.sub(
        r'{%\s*url\s+\'(.*?)\'\s*(.*?)\s*%}',
        lambda match: f"@url('{match.group(1)}', [{', '.join(match.group(2).split())}])",
        content_without_comments
    )
    
    for comment in extracted_comments:
        content_without_comments = content_without_comments.replace('{#COMMENT#}', comment, 1)

    return content_without_comments
