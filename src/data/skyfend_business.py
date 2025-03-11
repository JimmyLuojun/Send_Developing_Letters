from docx import Document# docx is a python library, which is used to read the word document; while document is a class in the docx library;
# function is a block of code that is used to perform a specific task; do we always need to pass parameters to the function? the answer is no, we can pass parameters to the function, but we can also pass no parameters to the function;


def read_skyfend_business(docx_file): # docx_file is a parameter; it is a path to the word document instead of the word document itself;
    """
    Reads Skyfend's main business from a Word document.
    
    :param docx_file: Path to the Word document.
    :return: Text content of the document.
    """
    # try is used to catch the error;
    try:# besides the try, we can also use else and finally; the way to use else and finally is to put the code in the else and finally block; the difference between try and else is that try is used to catch the error, and else is used to execute the code when the error is not caught; the difference between try and finally is that finally is used to execute the code after the try block, regardless of whether the error is caught or not;
        doc = Document(docx_file) #document is a class in the docx library;
        return "\n".join([para.text for para in doc.paragraphs])# \n is a string meaning a new line; join is a method that is used to join the elements of the list into a string;
    except Exception as e:# exception is a class in python; the difference between try and except is that try is used to catch the error, and except is used to handle the error;
        print(f"Error reading Skyfend's business document: {e}")
        return "" # return's default value is None; when we use print() method to print return, it will print None;

if __name__ == "__main__": # __name__ is a special variable in python, it is used to check if the file is run directly or imported;when  the file is run directly, __name__ is automatically set to "__main__",so __name__ == "__main__" is true;
    skyfend_business = read_skyfend_business("data/raw/skyfend_business.docx")
    print("Skyfend's main business:", skyfend_business)
