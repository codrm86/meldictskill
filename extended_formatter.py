from string import Formatter

class ExtendedFormatter(Formatter):
    """An extended format string formatter

    Formatter with extended conversion symbol
    """
    def convert_field(self, value, conversion):
        """ Extend conversion symbol
        Following additional symbol has been added
        * l: convert to string and low case
        * u: convert to string and up case
        * c: convert to string and capitalize

        default are:
        * s: convert with str()
        * r: convert with repr()
        * a: convert with ascii()
        """

        match conversion:
            case None:
                return value
            case "u":
                return str(value).upper()
            case "l":
                return str(value).lower()
            case "c":
                return str(value).capitalize()

        # Do the default conversion or raise error if no matching conversion found
        return super(ExtendedFormatter, self).convert_field(value, conversion)