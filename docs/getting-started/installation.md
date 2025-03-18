# Prerequisites

You will need Python installed and your favorite package and environment manager. This guide will use Poetry. If you do not have Poetry installed, you can install it by following the [official installation guide](https://python-poetry.org/docs/#installation).

You will also need to have Docker installed to follow most of the future tutorials.

##  Create a New Poetry Project

Run the following command to create a new Poetry project:  
```bash
poetry new my_project
```
Replace `my_project` with the desired name of your project.

Move into the newly created project directory:  
```bash
cd my_project
```

Poetry automatically manages a virtual environment for your project. To activate it, run:  
```bash
poetry shell
```

# Install the Library  
Use Poetry to add the library as a dependency:  
```bash
poetry add reagent[cli]
```

This will also include the Reagent CLI which we will use for the tutorials.




