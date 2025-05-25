from util.config_generator import ConfigGenerator
import sys

if __name__ == "__main__":
    generator = ConfigGenerator(sys.argv[1])
    generator.load_config()
    generator.execute()