import openai
import json
import Levenshtein

client = openai.OpenAI()

def extract_order_details(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """The following text is a fax order for hardware parts. Extract structured 
            order data from this order, specifically customer information and the products being ordered. Product names 
            will be written in Japanese. Product models will consist of English letters and numbers (eg SD-10
            or DXY). If product models are included in the order then do not include the product names in the output.
            However if the products are listed by their names only then do not attempt to include the product models 
            in the output. The company receiving the orders is called Best Parts, and so the customer name will always be 
            something other than Best Parts"""},
            {"role": "user", "content": text}
        ],
        functions=[
            {
                "name": "parse_order",
                "description": "Extracts structured order data from unstructured text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "address": {"type": "string"},
                                "contact_person": {"type": "string"},
                                "phone": {"type": "string"},
                                "fax": {"type": "string"}
                            },
                            "required": ["name", "address", "contact_person", "phone", "fax"]
                        },
                        "order_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_name": {"type": "string"},
                                    "model": {"type": "string"},
                                    "quantity": {"type": "integer"}
                                },
                                "required": ["quantity"]
                            }
                        }
                    },
                    "required": ["customer", "order_items"]
                }
            }
        ],
        function_call={"name": "parse_order"}  # Explicitly call the function
    )

    function_args = response.choices[0].message.function_call.arguments
    return json.loads(function_args)  # Convert JSON string to Python dict

def find_best_customer_with_openai(detected_name, customer_list):
    """Use GPT-4 Turbo to find the best matching customer and return structured JSON."""
    
    # Convert customer list to a string format for the LLM
    customer_entries = [
        {
            "id": customer["node"]["id"],
            "name_one": customer["node"]["name_one"].strip(),
            "name_two": customer["node"]["name_two"].strip()
        }
        for customer in customer_list
    ]
    
    # Create a system message instructing GPT-4 Turbo to return structured JSON
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that identifies the best-matching customer from a list based on the detected name. "
                                          "You MUST return a JSON object exactly matching the format of the customer entries provided."},
            {"role": "user", "content": f"The detected customer name is: '{detected_name}'.\n"
                                        f"Here is a list of possible customer entries:\n"
                                        f"{json.dumps(customer_entries, ensure_ascii=False, indent=2)}\n"
                                        f"Return ONLY the best-matching entry as a valid JSON object with keys: id, name_one, name_two. DO NOT include any explanation or extra text."}
        ],
        response_format={"type": "json_object"}
    )

    # Parse the response JSON
    best_match = json.loads(response.choices[0].message.content)

    return best_match

def find_best_shipping_with_openai(detected_address, address_list):
    """Use GPT-4o-mini to find the best matching customer and return structured JSON."""
    
    # Convert customer list to a string format for the LLM
    address_entries = [
        {
            "id": address["node"]["id"],
            "name_one": address["node"]["name_one"].strip(),
            "name_two": address["node"]["name_two"].strip(),
            "phone": address["node"]["phone"].strip(),
            "fax": address["node"]["fax"].strip(),
            "address_city": address["node"]["address_city"].strip(),
            "address_street": address["node"]["address_street"].strip()
            
        }
        for address in address_list
    ]
    
    # Create a system message instructing GPT-4 Turbo to return structured JSON
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that identifies the best-matching address from a list based on the detected address. "
                                          "You MUST return a JSON object exactly matching the format of the address entries provided."},
            {"role": "user", "content": f"The detected address is: '{detected_address}'.\n"
                                        f"Here is a list of possible address entries:\n"
                                        f"{json.dumps(address_entries, ensure_ascii=False, indent=2)}\n"
                                        f"Return ONLY the best-matching entry as a valid JSON object with keys: id, name_one, name_two, phone, fax, address_city, address_street.\n"
                                        f"DO NOT include any explanation or extra text."}
        ],
        response_format={"type": "json_object"}
    )

    # Parse the response JSON
    best_match = json.loads(response.choices[0].message.content)

    return best_match

def get_order_info(dtd):
    parsed_order = extract_order_details(str(dtd))
    #get customer
    detected_customer = parsed_order['customer']['name']

    customers_list = sorted(customers_result, 
                               key=lambda x: Levenshtein.distance(detected_customer, 
                                                                  f"{x['node']['name_one']} {x['node']['name_two']}"))
    customers_list = customers_list[:10]
    best_customer_match = find_best_customer_with_openai(detected_customer, customers_list)
    best_customer_id = best_customer_match['id']
    
    #get shipping address
    customer_info = str(parsed_order['customer'])
    address_list = sorted(shippings_result, 
                               key=lambda x: Levenshtein.distance(customer_info, 
                                                                  f"{x['node']['name_one']} {x['node']['name_two']} {x['node']['phone']} {x['node']['fax']} {x['node']['address_city']} {x['node']['address_street']}"))
    address_list_cid = [x for x in address_list if x['node']['customer_id']==best_customer_id]
    if len(address_list_cid) > 0:
        address_list = address_list_cid
    address_list = address_list[:10]
    for x in address_list:
        print(x)
    best_address_match = find_best_shipping_with_openai(customer_info, address_list)
    
    #get products
    product_matches = []
    for x in parsed_order['order_items']:
        if 'model' in x:
            detected_product = x['model']
            products_list = sorted(products_result, 
                                   key=lambda x: Levenshtein.distance(detected_product, 
                                                                      f"{x['node']['code']}"))
            product_matches.append(products_list[0]['node'])
        elif 'product_name' in x:
            detected_product = x['product_name']
            products_list = sorted(products_result, 
                                   key=lambda x: Levenshtein.distance(detected_customer, 
                                                                      f"{x['node']['name']}"))
            product_matches.append(products_list[0]['node'])
    
    return best_customer_match, best_address_match, product_matches

if __name__ == "__main__":
    from PIL import Image
    import pandas as pd

    with open('document_text_data_test.json', 'r') as f:
        dtd = json.load(f)
    customers = pd.read_csv('customers.csv')
    customers_result = [{'node':{'name_one':row['Name1'], 
                                 'name_two':row['Name2'], 
                                 'id':row['ID']}} for index, row in customers.iterrows()]
    shippings_result = [{'node':{'name_one':row['Name1'],
        'name_two':row['Name2'],
        'id':row['ID'],
         'customer_id':row['ID'],
         'fax':row['Fax'],
         'phone':row['Phone'],
         'address_city':row['Address_City'],
         'address_street':row['Address_Street']}} for index, row in customers.iterrows()]
    products = pd.read_csv('products.csv')
    products['id'] = range(100)
    products_result = [{'node':{'code':row['Part Number'],
                                'name':row['Part Name'],
                                'id':row['id']}} for index, row in products.iterrows()]
    best_customer_match, best_address_match, product_matches = get_order_info(dtd)
    print('BEST CUSTOMER MATCH:')
    print(best_customer_match)
    print('BEST ADDRESS MATCH:')
    print(best_address_match)
    print('PRODUCT MATCHES:')
    print(product_matches)