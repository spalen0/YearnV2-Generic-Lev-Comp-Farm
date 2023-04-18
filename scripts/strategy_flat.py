from brownie import LevCompFactory

def main():
    with open('LevCompFactory.sol', 'w') as f:
        LevCompFactory.get_verification_info()
        f.write(LevCompFactory._flattener.flattened_source)
