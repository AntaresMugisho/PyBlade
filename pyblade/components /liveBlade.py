import importlib
import pkgutil
from django.http import JsonResponse, HttpResponseRedirect
import json
from urllib.parse import urlencode
from .base import Component

# Dictionary to store initialized components by their IDs
components = {}

def initialize_components():
    """
    Initializes all components by dynamically loading them from the 'components' package. 
    It checks if the class is a subclass of Component and instantiates it, adding 
    it to the `components` dictionary.
    """
    package = 'components'
    for _, module_name, _ in pkgutil.iter_modules([package]):
        # Dynamically import each module in the 'components' package
        module = importlib.import_module(f"{package}.{module_name}")
        for name in dir(module):
            # For each class in the module, check if it is a subclass of Component
            cls = getattr(module, name)
            if isinstance(cls, type) and issubclass(cls, Component) and cls is not Component:
                # Create an instance of the component and add it to the components dictionary
                component_instance = cls(name.lower())  
                components[component_instance.id] = component_instance

# Initialize all components when the script is loaded
initialize_components()

def LiveBlade(request):
    """
    Handles the POST request to interact with a specific component's method. 
    It extracts data from the request, locates the appropriate component, 
    and calls the requested method with the provided parameters.

    If an error occurs, it redirects to an error page with an error message.
    If successful, it returns a JSON response with the rendered HTML.

    Args:
        request: The HTTP request object containing POST data.

    Returns:
        JsonResponse or HttpResponseRedirect: Returns either a JSON response containing the 
        HTML content or a redirect in case of an error.
    """
    if request.method == 'POST':
        try:
            # Extract data and files from the request
            data = request.POST.dict()
            files_data = request.FILES

            print('Received data:', data)

            # Get the component ID and method name from the request
            component_id = data.get('component')  
            method_name = data.get('method') 
            print(f"Component ID: {component_id}, Method: {method_name}") 

            # Locate the component using the ID
            component = components.get(component_id)

            if component is None:
                # Handle case where component is not found
                error_message = f"Component with ID {component_id} not found"
                print(error_message)
                params = urlencode({'error': error_message})
                return HttpResponseRedirect(f'/bladeError?{params}')
            
            if not hasattr(component, method_name):
                # Handle case where the method is not found in the component
                error_message = f"Method {method_name} not found in component {component_id}"
                print(error_message)
                params = urlencode({'error': error_message})
                return HttpResponseRedirect(f'/bladeError?{params}')

            # Get the method from the component
            method = getattr(component, method_name)

            formatted_params = {}
            print(files_data, 'data')
            # Format the parameters from the request
            for key in data.keys():
                if key.startswith('param'):
                    formatted_params[key] = data[key]
                    param = json.loads(formatted_params.get("param0"))
                    param = param.get('param', []) if not isinstance(param, list) else param
                    # Replace dynamic values with state values if needed
                    for i in param:
                        if isinstance(i, dict):
                            value = i.get("value")
                            if value and value.startswith("$"):
                                state_value = component.state.get(value[1:])
                                if state_value is not None:
                                    i['value'] = state_value  
                                    i['name'] = i['name'][1:]

                    formatted_params = param
            if files_data:
                # If files are attached, include them in the parameters
                print(f"Received files: {files_data}") 
                formatted_params['files'] = files_data 

            html_response = ''
            # If there are no parameters, call the method without parameters
            if len(formatted_params) == 0:
                html_response = method()
                # If the method returns a redirect URL, handle it
                if html_response.get("redirect"):
                    return HttpResponseRedirect(html_response.get("url"))
            else:
                # Call the method with the formatted parameters
                html_response = method(formatted_params)

            # Return the response as JSON
            return JsonResponse({'html': html_response})

        except (ValueError, KeyError, TypeError) as e:
            # Handle exceptions and redirect to the error page
            error_message = f"Error processing request: {e}"
            print(error_message)
            params = urlencode({'error': error_message})
            return HttpResponseRedirect(f'/bladeError?{params}')
    else:
        # If the method is not POST, return a 405 Method Not Allowed error
        return JsonResponse({'error': 'Method not allowed'}, status=405)
