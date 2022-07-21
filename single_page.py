from urllib import request, error
from datetime import date
import time
import json

# the error class
class MaxHTTPReqError(Exception):
  '''
  Exception raised if too many consecutive HTTP requests fail.

  Args:
    max_req (str): value of the maximum HTTP requests parameter
  '''

  def __init__(self, max_req):
      self.max_req = max_req
      self.message = f'The maximum threshold of {max_req} HTTP requests has been reached.'
      super().__init__(self.message)

def get_relevant_info(url: str, max_req: int = 5) -> dict:
  '''
  Provide an URL to the function and get a dictionary with imoprtant metrics to measure PageSpeed insights.

  Args:
    url (str): the URL whose information we want to know.
  
  Returns:
    relevant_info (dict): dictionary that contains the relevant fields that want to be known.
  
  '''
  print(f'Extracting relevant information for: {url}')
  
  # Make API request
  
  n_req = 0
  while True:
    try:
      req = request.urlopen('https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url={}/&strategy=mobile'.format(url))
      break
    except error.HTTPError:
      n_req =+ 1
      if n_req >= max_req:
        raise MaxHTTPReqError(max_req)
      print('Too many requests. Trying again...')
      time.sleep(5)

  result = req.read().decode('UTF-8')

  # Convert to json format
  result_json = json.loads(result)

  # Extract relevant fields
  relevant_info = {
      'URL': url,
      'Performance Score': result_json.get('lighthouseResult', {}).get('categories', {}).get('performance', {}).get('score', ''),
      'Time to Interactive (in seconds)': result_json.get('lighthouseResult', {}).get('audits', {}).get('interactive', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'Largest Contentful Paint': result_json.get('lighthouseResult', {}).get('audits', {}).get('largest-contentful-paint', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'First Contentful Paint  (in seconds)': result_json.get('lighthouseResult', {}).get('audits', {}).get('first-contentful-paint', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'First Meaningful Paint (in seconds)': result_json.get('lighthouseResult', {}).get('audits', {}).get('first-meaningful-paint', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'First Input Delay (in ms)': result_json.get('loadingExperience', {}).get('metrics', {}).get('FIRST_INPUT_DELAY_MS', {}).get('percentile', ''),
      'Cumulative Layout Shift': result_json.get('lighthouseResult', {}).get('audits', {}).get('cumulative-layout-shift', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'Server Response Time': result_json.get('lighthouseResult', {}).get('audits', {}).get('server-response-time', {}).get('numericValue', ''),
      'Speed Index  (in seconds)': result_json.get('lighthouseResult', {}).get('audits', {}).get('speed-index', {}).get('displayValue', '').replace(u'\xa0', '')[:-1],
      'Last Time Report Ran': date.today().strftime("%Y/%m/%d")
  }

  # If all fields were retrieved, status will be complete; otherwise, it will be incomplete
  relevant_info['status'] = 'Complete' if all(relevant_info.values()) else 'Incomplete'

  return relevant_info

def page_speed_single_call(request):
    
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    
    # get the url 
    request_json = request.get_json()
    if request.args and 'url' in request.args:
        url =  request.args.get('url')
    elif request_json and 'url' in request_json:
        url =  request_json['url']
    else:
        return f'Need url!'

    relevant_info = get_relevant_info(url)
    relevant_info = json.dumps(relevant_info)

    return relevant_info