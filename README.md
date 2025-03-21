Initial version of a final project for the course. 

We are working with a Japanese hardware company called Best Parts as one of our projects. Many of the orders for parts that this company receives from customers are faxes, as faxes are still prevalent in Japan. We are trying to automate the task of looking at the faxes and getting the order information (customer who sent the order, shipping address, parts being ordered and their quantities). We have done this by getting the fax text with OCR and then applying a sort of complicated rule based system on the OCR result to get this information. This process can fail for some faxes if they have a unique/irregular format, so I am trying to use OpenAI features to parse through the text instead. Below are the files used:

products.csv and customers.csv: Files that have fake products and customers. The real products and customers are stored in a postgres database but this information is sensitive, especially the customers table, so just using fake data for testing.

test_fax.jpg: Fake order form fax. The customer is one of the customers in the csv file and the 4 products are products somewhere in the products.csv file. Some of the product names and codes are purposely written slightly incorrectly to emulate real fax data. 

document_text_data.json: List of characters and their locations within the test fax image. Normally we use google cloud ocr to get this data but this requires google cloud credentials, so this repo just uses the already gotten text. This is the same format as what is outputted from get_text_from_image.py though. 

get_fax_info.py: Code for getting the fax information. This is an initial version so I am just using individual calls to the openai API. I will attempt to use chains/agents for the final version. Process is outlined below
* Get fax info with structured output from openai. This gets the detected customer, address, and products, but these may or may not actually be in the database. Anything in the final output must be an item that actually exists in the database so we need find the entries in the database that most closely match what was detected from openai.
* Find closest customer. First step is to take the detected customer name and find the 10 customers in the database whose full name (name_one plus name_two entry) have the closest Levenshtein distance. Then make another prompt that has LLM find the customer entry amongst those 10 that most closely match the detected customer name. Although you could just take the customer with the lowest Levenshtein distance, there may be cases where the actual correct customer is not the one with the lowest Levenshtein distance, so an LLM may be able to mose closely look at the customers and how well they match with the detected name. 
* Find closest shipping address. Essentially the same process as finding the closest customer except use extra fields (phone, fax, address city, address street).
* Find closest products. For each detected product, find the product in the database that has the lowest Levenshtein distance. I did try using another prompt for this like with finding the customer and shipping but the LLM can behave strangely when it doesn't find a good match in the database, like make up products on the fly. 

Once the customer, shipping address and products are detected, this information would normally get sent to the project backend, but this repo just shows the inference side of the project. 