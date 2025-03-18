## Prerequisites

You will need Python installed and your favorite package and environment manager. This guide will use Poetry. If you do not have Poetry installed, you can install it by following the [official installation guide](https://python-poetry.org/docs/#installation).

You will also need to have Docker installed to follow most of the future tutorials.

## Steps to Create a New Poetry Project

1. **Initialize a New Project**  
    Run the following command to create a new Poetry project:  
    ```bash
    poetry new my_project
    ```
    Replace `my_project` with the desired name of your project.

2. **Navigate to the Project Directory**  
    Move into the newly created project directory:  
    ```bash
    cd my_project
    ```

3. **Install the Library**  
    Use Poetry to add the library as a dependency:  
    ```bash
    poetry add reagent[cli]
    ```

4. **Activate the Virtual Environment**  
    Poetry automatically manages a virtual environment for your project. To activate it, run:  
    ```bash
    poetry shell
    ```


