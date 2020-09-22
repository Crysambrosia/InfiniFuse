import gzip
import struct
import zlib

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12

# NBT tag data model and interface
class NBT:
    # Contructor, does NOT decode/decompress
    def __init__(self, ID=0, payload=None, name=None, compression=None):
    
            # Tag ID
            self.ID = ID
            
            # Tag payload
            if payload is not None and self.ID != 0:
                self.payload = payload
            
            # Store type info
            if self.ID == TAG_LIST:
                try:
                    elementID = self[0].ID
                except IndexError:
                    elementID = TAG_END
                self.typeStr = f'{NBT.IDstr(self.ID)}({NBT.IDstr(elementID)})'
            else:
                # Type as str
                self.typeStr = NBT.IDstr(self.ID)
                    
            # Tag name
            if name is not None:
                self.name = name
                
            # Compression method
            if compression is not None:
                self.compression = compression

    # Test if two tags are the same
    def __eq__(self, other):
        if type(other) != NBT:
            print('Other was not NBT')
            return False
        elif self.ID != other.ID:
            print(f'ID mismatch with {self.ID} and {other.ID}')
        else:
            # For arrays / compounds / lists
            if (
                self.ID == TAG_BYTE_ARRAY 
                or self.ID == TAG_LIST
                or self.ID == TAG_COMPOUND
                or self.ID == TAG_INT_ARRAY
                or self.ID == TAG_LONG_ARRAY
            ):
                # Make one iteratable out of both
                zipped = zip(self.payload, other.payload)
                # Recursively compare all values
                for selfElement, otherElement in zipped:
                    if selfElement != otherElement:
                        print(f'Element mismatch with {selfElement} and {otherElement}')
                        return False
                        break
                else:
                    return True
                    
            elif self.ID == 0:
                return True
            else:
                # Compare values
                value = self.payload == other.payload
                if value == False:
                    print(f'Value mismatch with {self.payload} and {other.payload}')
                return value
    
    
    # Length of array tags
    def __len__(self):
        return len(self.payload)

    # Subscript accessor override
    def __getitem__(self, key):
        return self.payload[key]
    
    # Subscript assignment override
    def __setitem__(self, key, value):

        # ID of item
        itemID = self[key].ID

        # Check types ==
        if type(value) != type(self[key].payload):
            raise TypeError (f'Cannot assign {str(type(value))} to {self[key].typeStr}')
           
        # Check value is within bounds
        if itemID <= 6:
            if itemID == TAG_BYTE:
                minimum = 0
                maximum = 255
                
            elif itemID == TAG_SHORT or itemID == TAG_INT or itemID == TAG_LONG:
                minimum = -2**( 8*(itemID-1) )
                maximum = 2**( 8*(itemID-1) ) -1
                
            elif itemID == TAG_FLOAT or itemID == TAG_DOUBLE:
                minimum = -2**( 8*(itemID-3) )
                maximum = 2**( 8*(itemID-3) ) -1
                
            if value<minimum or value>maximum:
                raise ValueError( f'Value for {self[key].typeStr} must be between {minimum} and {maximum}')
                
        # Assign Value
        self[key].payload = value
    
    # Returns SNBT
    def __repr__(self):
    
        snbt = ''
        if self.ID == TAG_END:
            pass
        elif (
            self.ID == TAG_BYTE 
            or self.ID == TAG_SHORT
            or self.ID == TAG_INT 
            or self.ID == TAG_LONG 
            or self.ID == TAG_DOUBLE 
            or self.ID == TAG_FLOAT
        ):
         
            snbt += str(self.payload)
            
            # Choose letter to append to value
            if self.ID == TAG_BYTE:
                snbt += 'b'
            elif self.ID == TAG_SHORT:
                snbt += 's'
            elif self.ID == TAG_LONG:
                snbt += 'l'
            elif self.ID == TAG_FLOAT:
                snbt += 'f'
            elif self.ID == TAG_DOUBLE:
                snbt += 'd'
            
        elif self.ID == TAG_STRING:
            
            # Opening quote
            snbt += '\''
            
            # Write characters, escape quotes
            for character in self.payload:
                if character == '\'':
                    # Both backslash and quote need escaping, hence the \\\
                    snbt += '\\\''
                else:
                    snbt += character
                
            # Closing quote
            snbt += '\''
                
        elif (
            self.ID==TAG_BYTE_ARRAY 
            or self.ID==TAG_LIST 
            or self.ID==TAG_INT_ARRAY 
            or self.ID==TAG_LONG_ARRAY
        ):
            
            # Opening square bracket
            snbt += '['
            
            if self.ID == TAG_BYTE_ARRAY:
                snbt += 'B;'
            elif self.ID == TAG_INT_ARRAY:
                snbt += 'I;'
            elif self.ID == TAG_LONG_ARRAY:
                snbt += 'L;'
            
            # Used to know if comma needed
            i = len(self.payload)
            
            for element in self.payload:
                snbt += repr(element)
                
                # Add comma if not last item
                i -= 1
                if i > 0:
                    snbt += ','

            # Closing square bracket
            snbt += ']'
            
        elif self.ID == TAG_COMPOUND:
            
            # Opening Curly Bracket
            snbt += '{'
            
            # Used to know if comma needed
            i = len(self.payload)
            
            # Add all elements
            for element in self.payload:
                snbt += f'{element}:{self[element]}'
                
                # Add comma if not last item
                i -= 1
                if i > 0:
                    snbt += ','
                
            # Closing Curly Bracket
            snbt += '}'
            
        return snbt

    # Alias of __repr__
    def __str__(self):
        return repr(self)
        
    # Decodes (compressed) bytes -> NBT
    def decode( nbt = b'\x00', compression = None ):

        # Decode individual payload
        def decodePayload(tagID):
            
            # TagIDs are only defined up to 12
            if tagID > 12:
                raise RuntimeError('Invalid tagID : ' + str(tagID) )
                
            if tagID == TAG_COMPOUND:
            
                payload = {}
                # Checked once before in case of empty compound
                itemID = decodePayload(TAG_BYTE)
                
                while itemID != 0:
                    itemName = decodePayload(TAG_STRING)
                    itemPayload = decodePayload(itemID)
                    try :
                        payload[itemName] = NBT(
                            ID=itemID,
                            payload=itemPayload,
                            name=itemName
                        )
                    except TypeError:
                        raise TypeError(str(itemID) + ' ' + str(itemName) + ' ' + str(itemPayload))
                        
                    # ID of next item
                    itemID = decodePayload(TAG_BYTE)
                
            else:
                
                if (
                    tagID == TAG_BYTE_ARRAY 
                    or tagID == TAG_LIST 
                    or tagID == TAG_INT_ARRAY 
                    or tagID == TAG_LONG_ARRAY
                ):
                
                    # Find recursive element ID
                    if tagID == TAG_BYTE_ARRAY:
                        itemID = TAG_BYTE
                        
                    elif tagID == TAG_LIST:
                        itemID = decodePayload(TAG_BYTE)
                        
                    elif tagID == TAG_INT_ARRAY:
                        itemID = TAG_INT
                        
                    elif tagID == TAG_LONG_ARRAY:
                        itemID = TAG_LONG
                
                    # Make Payload
                    payload = []
                    
                    size = decodePayload(TAG_INT)
                    for i in range(size):
                        itemPayload = decodePayload(itemID)
                        payload.append(NBT(ID=itemID, payload=itemPayload))
                        
                else:
                    # Calculate length
                    if (
                        tagID == TAG_BYTE 
                        or tagID == TAG_SHORT 
                        or tagID == TAG_INT 
                        or tagID == TAG_LONG
                    ):
                        payloadLength = 2 ** (tagID-1)
                        
                    elif tagID == TAG_FLOAT or tagID == TAG_DOUBLE:
                        payloadLength = 2 ** (tagID-3)
                        
                    elif tagID == TAG_STRING:
                        payloadLength = decodePayload(TAG_SHORT)
                    
                    # Read Payload
                    payload = bytearray()
                    try:
                        for i in range(payloadLength):
                            nextByte = nbt.__next__()
                            if type(nextByte) == int:
                                payload.append(nextByte)
                            elif type(nextByte) == bytes:
                                payload += nextByte
                            # Sometimes the file returns ints and sometimes bytes
                            # If I ever find out why maybe I can simplify this
                    except StopIteration:
                        pass

                    # Format Payload
                    if tagID == TAG_BYTE:
                        payload = int.from_bytes(payload, byteorder='big')
                        
                    elif (
                        tagID == TAG_SHORT 
                        or tagID == TAG_INT 
                        or tagID == TAG_LONG
                    ):
                        payload = int.from_bytes(payload, byteorder='big', signed=True)
                        
                    elif tagID == TAG_FLOAT or tagID == TAG_DOUBLE:
                        
                        # Choose unpack mode
                        if tagID == TAG_FLOAT:
                            mode = '>f'
                        elif tagID == TAG_DOUBLE:
                            mode = '>d'
                        
                        # Unpack Payload
                        [payload] = struct.unpack(mode, payload)
                        
                    elif tagID == TAG_STRING:
                        try:
                            payload = payload.decode()
                        except UnicodeDecodeError:
                            raise RuntimeError('Cannot decode '+ str(payload) +' to unicode')
                        
            return payload
          
        # Try all methods if compression is unknown
        if compression is None:
            for tryCompression in [3,1,2]:
                # Try uncompressed first to save computing time
                try:
                    payload = NBT.decode(nbt, tryCompression)
                    break
                except:
                    continue
            else:
                # Runs if all compression methods failed
                raise RuntimeError('Unknown compression method.')

        # Decompress and decode
        else:
        
            # Decompresss input
            if compression == 1:
                nbt = gzip.decompress(nbt)
            elif compression == 2:
                nbt = zlib.decompress(nbt)
            elif compression == 3:
                # 3 means no compression
                pass
            else:
                raise ValueError(f'Unknown compression method {compression}')
        
            # Make input iteratable,
            nbt = nbt.__iter__()
            
            # Get data
            tagID = decodePayload(TAG_BYTE)
            tagName = decodePayload(TAG_STRING)
            tagPayload = decodePayload(tagID)
            
            # Format as NBT
            payload = NBT(
                ID=tagID, 
                name=tagName, 
                payload=tagPayload,
                compression = compression
            )

        return payload

    # Encodes NBT -> (compressed) bytes
    def encode(self, newCompression = None):
    
        # Encode individual payload
        def encodePayload(tagID, tagPayload = {}):
            # TagIDs are only defined up to 12
            if tagID > 12:
                raise RuntimeError( 'Invalid tagID : ' + str(tagID) )
                
            # Create empty payload
            payload = bytearray()
            
            if tagID == TAG_COMPOUND:
                for element in tagPayload:
                    # Recursively encode
                    payload += tagPayload[element].encode()
                payload += (b'\x00')
                
            else:
                # For recursives
                if (
                    tagID == TAG_BYTE_ARRAY 
                    or tagID == TAG_LIST 
                    or tagID == TAG_INT_ARRAY
                    or tagID == TAG_LONG_ARRAY
                ):
                
                    if tagID == TAG_LIST:
                        # Find elementID
                        try:
                            elementID = tagPayload[0].ID
                        except IndexError:
                            elementID = TAG_END
                            
                        # Store elementID in payload
                        payload += encodePayload(TAG_BYTE, elementID)
                        
                    # Store length in payload 
                    payload += encodePayload(TAG_INT, len(tagPayload))
                    
                    # Make Payload
                    for element in tagPayload:
                        payload += encodePayload(element.ID, element.payload)
                    
                # For non-recursives
                else:
                    if tagID == TAG_BYTE:
                        payload += tagPayload.to_bytes(length=1, byteorder='big')
                        
                    elif (
                        tagID == TAG_SHORT
                        or tagID == TAG_INT
                        or tagID == TAG_LONG
                    ):
                            payload += tagPayload.to_bytes(length=(2**(tagID-1)), byteorder='big', signed=True)
                        
                    elif tagID==TAG_FLOAT or tagID==TAG_DOUBLE:
                        
                        # Choose unpack mode
                        if tagID == TAG_FLOAT:
                            mode = '>f'
                        elif tagID == TAG_DOUBLE:
                            mode = '>d'
                        payload += struct.pack(mode, tagPayload)
                        
                    elif tagID == TAG_STRING:
                        # For strings
                        tagPayload = tagPayload.encode()
                        payload += encodePayload(TAG_SHORT, len(tagPayload))
                        payload += tagPayload
                    
            return payload
        
        payload = bytearray()
        # Encode TAG_ID
        payload += encodePayload(TAG_BYTE, self.ID)

        # Encode name if applicable
        try:
            payload += encodePayload(TAG_STRING, self.name)
        except AttributeError:
            pass
        
        # Encode payload
        payload += encodePayload(self.ID, self.payload)
            
        # Find out compression method
        try:
            compression = newCompression if newCompression is not None else self.compression
        except AttributeError:
            # If compression is undefined, do not compress
            compression = 3
            
        # Compress payload
        # Recursions use 3, only outermost is compressed
        if compression == 1:
            payload = gzip.compress(payload)
        elif compression == 2:
            payload = zlib.compress(payload)
        elif compression == 3:
            # 3 means no compression
            pass
        else:
            raise ValueError(f'Unknown compression method {compression}')

        return payload

    # Get subtags, if applicable
    def keys(self):
        return self.payload.keys()
        
    # Returns tag type str of ID
    def IDstr(ID):
        if ID == TAG_END:
            return 'TAG_End'
        elif ID == TAG_BYTE:
            return 'TAG_Byte'
        elif ID == TAG_SHORT:
            return 'TAG_Short'
        elif ID == TAG_INT:
            return 'TAG_Int'
        elif ID == TAG_LONG:
            return 'TAG_Long'
        elif ID == TAG_FLOAT:
            return 'TAG_Float'
        elif ID == TAG_DOUBLE:
            return 'TAG_Double'
        elif ID == TAG_BYTE_ARRAY:
            return 'TAG_Byte_Array'
        elif ID == TAG_STRING:
            return 'TAG_String'
        elif ID == TAG_LIST:
            return 'TAG_List'
        elif ID == TAG_COMPOUND:
            return 'TAG_Compound'
        elif ID == TAG_INT_ARRAY:
            return 'TAG_Int_Array'
        elif ID == TAG_LONG_ARRAY:
            return 'TAG_Long_Array'