KhubeEdit blockstate file specification :

Template file looks like this :

{
    "parents" : [],
    "properties" : {
        "example" : ["defaultValue", "otherValue1", "otherValue2"]
    }
}

Properties are loaded from the parents, their parents, and so forth until the root is reached
Circular hierarchies will result in an exception
Value 0 is considered the default (see example above)