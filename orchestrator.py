import base64
import json
import functions_framework
import aiohttp 
import asyncio
import json
import pandas as pd

from google.cloud import storage

def upload_blob(bucket_name, blob_name, local_path):
    """
    upload object from local path to blob storage

        bucket_name (str): name of bucket
        blob_name   (str): name of blob
        local_path  (str): name of local_path
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    print(
            "Uploaded local storage object {} to bucket {} to blob file {}.".format(
                local_path, bucket_name, blob_name
            )
        )


def download_blob(bucket_name, blob_name, local_path):
    """
    download object from blob to local storage

        bucket_name (str): name of bucket
        blob_name   (str): name of blob
        local_path  (str): name of local_path
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_path)
    print(
            "Downloaded storage object {} from bucket {} to local file {}.".format(
                blob_name, bucket_name, local_path
            )
        )


def get_tasks(session, endpoint, urls, API_KEY):
    """
    collect tasks (coroutines) in a list 
        
        session  (str)       : name of session
        endpoint (str)       : name of endpoint
        urls     (List[str]) : name of local_path
        API_KEY  (str)       : Key for API permission
    """
    tasks = []
    for url in urls:   
        payload ={'url':f'{url}', 'key': API_KEY}
        tasks.append(session.get(endpoint, params=payload))
    return tasks

# function is asynchronous, but loop inside is not!
async def do_calls(urls, API_KEY, endpoint):
    """
    Function to make the async API calls 
        
        urls     (List[str]) : name of local_path
        API_KEY  (str)       : Key for API permission
    """
            
    results = []
    # need to add async to this
    async with aiohttp.ClientSession() as session:
        tasks = get_tasks(session, endpoint, urls, API_KEY)
        responses = await asyncio.gather(*tasks) 

        for response in responses:
            # output of gather is a list of awaitable objects
            results.append(await response.json(content_type=None))

        return results

@functions_framework.cloud_event
def orchestrator(cloud_event):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         event (dict): Event payload.
         context (google.cloud.functions.Context): Metadata for the event.
    """
    
    attributes = cloud_event.data["message"]["attributes"]
    bucket_name = attributes["bucket_name"]
    url_file = attributes["blob_name_url"]
    master_file = attributes["blob_name_master"]
    endpoint = attributes["endpoint"]

    print(f"Using bucket_name: {bucket_name}")
    print(f"Using url_file: {url_file}")
    print(f"Using master_file: {master_file}")
    print(f"Using end point: {endpoint}")

    local_path='/tmp/urls.txt'
    download_blob(bucket_name, url_file, local_path)

    file = open(local_path, 'r')
    urls = [l.strip() for l in file.readlines()]

    print(f"Urls are: {urls}")

    secret_locations = '/secrets/PageSpeedSecret'

    with open(secret_locations) as f:
        API_KEY = f.readlines()[0]

    # get daily reads and save in df_daily
    results = asyncio.run(do_calls(urls, API_KEY, endpoint))
    parsed_results = json.loads(json.dumps(results))
    df_daily = pd.DataFrame(parsed_results)

    # load df_master
    local_path='/tmp/master_file.csv'
    download_blob(bucket_name, master_file, local_path)
    df_master = pd.read_csv(local_path)
    
    # concat, save and upload
    df_master = pd.concat([df_master, df_daily]).reset_index(drop=True)
    df_master.to_csv(local_path, index=False)
    upload_blob(bucket_name, 'master_file.csv', local_path)