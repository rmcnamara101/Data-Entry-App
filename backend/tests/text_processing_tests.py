

def cleanup_given_names(given_names):
        """
        Cleans up the given names by removing quoted text.
        """
        for i in range(len(given_names)):
            if given_names[i] == "'" or given_names[i] == '"':
                break
        given_names = given_names[:i]
        print(given_names)
        return given_names
        


def given_names(input, expected_output):
    cleaned_texr = cleanup_given_names(input)
    assert cleaned_texr == expected_output
    print("Test Passed!")

input = 'Christopher"Chris"'
expected_output = 'Christopher'

given_names(input, expected_output)