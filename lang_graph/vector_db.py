urls=[
    "https://lilianweng.github.io/posts/2023-06-23-agent/"
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/"
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/"
]



from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader

docs=[WebBaseLoader(url).load() for url in urls]
docs_list=[item for sublist in docs for item in sublist]

text_splitter=RecursiveCharacterTextSplitter.from_tiktoken_encoder()