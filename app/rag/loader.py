from langchain_community.document_loaders import TextLoader
import os

def load_documents():

    docs = []
    folder = "data/investment_reports"

    for file in os.listdir(folder):

        if file.endswith(".txt"):
            loader = TextLoader(os.path.join(folder, file))
            docs.extend(loader.load())

    return docs