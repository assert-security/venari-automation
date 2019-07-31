# Setting up for VSCode (Windows)

Follow these steps if you need to work in an virtual environment for any of the projects in this folder.

Install the Microsoft python extension

Create a virtual environment in this same folder as this readme:

```ps1
pip install virtualenv
py -m venv venv 
```

Enter the venv:

```ps1
.\venv\Scripts\Activate.ps1
```



Build the venari api and install it into the current venv:

```ps1
cd .\venari-client
pip install .
```



Now launch vscode from the `whitesnake` folder. You should see the python interpreter in the virtual environment now. Select it. When prompted, install the linter.

