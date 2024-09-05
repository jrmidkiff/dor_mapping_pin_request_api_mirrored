import json
import functools
import boto3

def get_creds(config_path: str, path:list=[]) -> dict: 
    '''
    Return a dictionary from a JSON file, where path is a list of hierarchical keys
    '''
    with open(config_path, 'r') as f:
        file = f.read()
        as_json = json.loads(file)
        creds = functools.reduce(dict.get, path, as_json) # path is the [][]...[] of  dict
    if creds == None: 
        raise(TypeError(f'Invalid db credentials, check config_path "{config_path}"'))
    return creds   

def get_aws_secret(secret_name: str) -> dict: 
    '''
    Get a secret from AWS Secrets Manager, returning dictionary
    '''
    secretsmanager = boto3.client('secretsmanager', region_name='us-east-1')
    rv = secretsmanager.get_secret_value(SecretId=secret_name)
    return json.loads(rv['SecretString'])
