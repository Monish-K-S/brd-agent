from parsers.response_parser import ResponseParser

parser = ResponseParser()

response = """
[
    {}
]
"""

parser.parse_document_analysis(response)
data = parser.parse_document_analysis(response)

print(data)
