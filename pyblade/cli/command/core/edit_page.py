def edit_html_file(file_path, new_html_content):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_html_content)
        
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(e)


