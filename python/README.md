# Setting up for VSCode (Windows)

Follow these steps if you need to work in an virtual environment for any of the projects in this folder.

Install the Microsoft python extension

Create a virtual environment in this same folder as this readme:

```ps1
pip install virtualenv
mkdir ~/.virtualenvs -Force
cd ~/.virtualenvs
py -m venv venariapi 
```

Enter the venv:

```ps1
~/.virtualenvs/venariapi/Scripts/Activate.ps1
```



Build the venari api and install it into the current virtual environment (from `<source>/python/venari-client`:

```ps1
pip install .
```

**Note**: We are not using `setup.py build/install` because it produces an egg, which is not supported by the VSCode python language server (no intellisense).

You can open VSCode in either the `venari-client` or `whitesnake` folder.

Select the python interpreter for the virtual environment you created above for the interpreter. This can be done from the command palette `Python: Select Interpreter`, or from task bar "Python" 

Enable Linting:

From the command palette select: `python: select linter` and pick `pylint`. VSCode should prompt you to install the linter.

**Note**: You have to open either the whitesnake or venari-client folders in VSCode for the modules to resolve. The whitesnake project will use the venari_api code that was installed via pip, while the venari-client code will resolve to the module source folder.



To test venariapi, there is an example cli that can be invoked. You can get help by running:

```ps1
python -m venariapi.examples.cli --help
```



# Create a credential profile

VenariApi requires a credential profile to be specified when accessing a master server. The information stored includes the OAuth `client secret` among other necessary parameters. It is currently stored as clear text in `~/venari_cli.json`. 

To create a credential profile, use the cli todo so by running the following:

```ps1
py -m venariapi.examples.cli --no_verify_ssl --url https://host.docker.internal:9000 login --client_id 5518f6f9-a3c2-4501-b4fa-dc183760ba4f
```

The secret can be found in `~/assert-security/jobnode-client-secret`

You can also create your own way of handling credentials. See the `venari_cli.json`above for the information required.

