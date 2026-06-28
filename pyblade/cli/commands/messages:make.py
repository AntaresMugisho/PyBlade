from pyblade.cli import BaseCommand

class Command(BaseCommand):
    """
    Runs over the entire source tree of the current directory and pulls out  
    all strings marked for translation.  
    It creates (or updates) a message    
    file in the conf/locale (in the      
    django tree) or locale (for projects 
    and applications) directory.         
                                                                   
    You must run this command with one   
    of either the --locale, --exclude,   
    or --all options.
    """

    name = "messages:make"
    aliases = ["make:messages"] # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade messages:make' command"""
        ...
