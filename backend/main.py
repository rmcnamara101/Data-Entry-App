# Description: Main entry point for the application. 
import logging
from logging_config import setup_logging
import numpy as np

def main():

    x = np.random.random((3,3)) - 1
    print(x)

if __name__ == '__main__':
    main()
