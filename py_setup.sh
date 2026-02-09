#!/bin/bash

# Set variables
PYTHON_VERSION=3.9.13
INSTALL_DIR=$(pwd)/localpython  # Set install directory to current directory
DOWNLOAD_DIR=$(pwd)/python_build
PYTHON_URL="https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tgz"
REQUIREMENTS_FILE=$(pwd)/requirements.txt  # Path to the requirements.txt file

# Function to check if a command exists
command_exists () {
    command -v "$1" >/dev/null 2>&1 ;
}

# Check for existing local Python installation
if [ -x "$INSTALL_DIR/bin/python3" ]; then
    echo "Found existing Python installation in $INSTALL_DIR."
else
    echo "No existing Python installation found. Installing Python $PYTHON_VERSION..."

    # Create directories
    mkdir -p $INSTALL_DIR
    mkdir -p $DOWNLOAD_DIR

    # Download Python source code
    cd $DOWNLOAD_DIR
    wget $PYTHON_URL

    # Extract the downloaded file
    tar -xzf Python-$PYTHON_VERSION.tgz
    cd Python-$PYTHON_VERSION

    # Configure the build for local installation
    ./configure --prefix=$INSTALL_DIR --enable-optimizations

    # Build and install Python locally
    make -j$(nproc)
    make install

    # Update PATH in the current shell session to include the local Python installation
    export PATH=$INSTALL_DIR/bin:$PATH

    # Verify the Python installation
    echo "Python installed at $INSTALL_DIR"
    python3 --version
fi

# Check for existing pip installation
if [ -x "$INSTALL_DIR/bin/pip3" ]; then
    echo "Found existing pip installation in $INSTALL_DIR."
else
    echo "No existing pip installation found. Installing pip..."

    # Install pip
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py --prefix=$INSTALL_DIR

    # Verify pip installation
    echo "Pip installed at $INSTALL_DIR"
    pip3 --version

    # Clean up
    rm get-pip.py
fi

# Install dependencies from requirements.txt if it exists
if [[ -f "$REQUIREMENTS_FILE" ]]; then
    echo "Installing dependencies from requirements.txt..."
    pip3 install --prefix=$INSTALL_DIR -r $REQUIREMENTS_FILE
else
    echo "requirements.txt not found, skipping dependency installation."
fi

echo "Local Python setup completed."
