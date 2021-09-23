
from . import abc

import hashlib

def build_table(name, schema, entities):

    if schema.get('type','') not in ['object', 'array']:
        return ''

    yield ''
    yield '.. _'+entities('/components/schemas/'+name)+':'
    yield ''
    yield name
    yield "'"*len(name)
    yield ''
    yield '.. list-table:: ' + name
    yield '    :header-rows: 1'
    yield '    :widths: 25 25 45 15'
    yield '    :class: longtable'
    yield ''    
    yield '    * - Attribute'
    yield '      - Type'
    yield '      - Description'
    yield '      - Mandatory'

    attributeValue = ''
    typeValue = ''
    descriptionValue = ''
    mandatoryValue = ''
    subtype = None
    mand=[]
    row = []
    for param in schema.keys():
        
        if param =='required':
            mand=schema[param]
        elif param=='properties':
            attributeValues = schema[param]
            
            
            for attribute in attributeValues.keys():
                if attribute in mand:
                    mandatoryValue = 'Yes'
                    
                row = []
                attributeValue = attribute
                if '$entity_ref' in attributeValue:
                    refatt=attributeValue.replace("#/components/schemas/",'')
                    row.append(refatt)
                else:
                    row.append('``'+attributeValue+'``')

                propertyValues = attributeValues[attribute]
                typerefvalue=''
                
                # do a first loop to initialize some fields
                for property in propertyValues.keys():
                    if property == 'type':
                        typeValue = str(propertyValues[property])+typerefvalue
                    elif property == 'description':
                        descriptionValue = str(propertyValues[property])
                
                for property in propertyValues.keys():
                    
                    if property == 'format':
                        if str(propertyValues[property])=='date':
                            typeValue += ' ('+str(propertyValues[property])+')'
                        elif str(propertyValues[property])=='date-time':
                            typeValue += ' (date & time)'
                            
                        elif str(propertyValues[property])=='byte':
                            typeValue += ' ('+'base64 encoded'+')' 
                        
                        elif str(propertyValues[property])=='binary':
                            typeValue += ' ('+str(propertyValues[property])+')'
                            
                        else:
                            typeValue += ' ('+str(propertyValues[property])+')'
                    
                        
                    elif property == 'items':
                        
                        if '$entity_ref' in propertyValues[property]:
                            refval = propertyValues[property]['$entity_ref']
                            
                            # add ref to the type
                            typerefvalue = ' of ' + ref2link(entities, refval)
                            typeValue += typerefvalue
                        elif 'properties' in   propertyValues[property]:
                            typeValue = 'Array of objects'
                            attributeValue += '[]'
                            subtype = propertyValues[property]

                    elif property == 'minItems':
                        descriptionValue += ' minItems: ' + str(propertyValues[property])
                    elif property == 'maxItems':
                        descriptionValue += ' maxItems: ' + str(propertyValues[property])

                    elif property == 'minLength':
                        descriptionValue += ' minLength: ' + str(propertyValues[property])
                    elif property == 'maxLength':
                        descriptionValue += ' maxLength: ' + str(propertyValues[property])
                    elif property == 'minimum':
                        descriptionValue += ' minimum: ' + str(propertyValues[property])
                    elif property == 'maximum':
                        descriptionValue += ' maximum: ' + str(propertyValues[property])
                    elif property == 'enum':
                        descriptionValue += ' Possible values are: '+', '.join(['``{}``'.format(x) for x in propertyValues[property]])
                    elif property == '$entity_ref':
                        if propertyValues['type'] == 'object':
                            typeValue = ref2link(entities, propertyValues[property])
                    elif property == 'properties' and propertyValues.get('type',None) in ['object',None]:
                        typeValue = 'Object'
                        subtype = propertyValues
                    elif property == 'properties' and propertyValues.get('type',None)!='object':
                        # Update the code accordingly
                        typkey2=propertyValues[property]['key']['$entity_ref']
                        typval2=propertyValues[property]['value']['$entity_ref']
                        
                        dictkval11=typkey2.replace('#/components/schemas/','')
                        dictkval12=typval2.replace('#/components/schemas/','')
                        dictkval='key : '+dictkval11 + ' ,' +'value : '+dictkval12
                        typeValue = dictkval
                row.append(typeValue)
                row.append(descriptionValue)
                row.append(mandatoryValue)
                yield '    * - ' + row[0]
                yield '      - ' + row[1]
                yield '      - ' + row[2]
                yield '      - ' + row[3]
                row = []
                if subtype:
                    print('*******')
                    # include the attributes of the sub-object (this is not a ref to another entity)
                    #for line in ...
                    # sub_head,sub_body = self._make_table_contents(swagger,subtype)
                    # for b in sub_body:
                    #     body.append([attributeValue+'.'+b[0]]+b[1:])
                    subtype = None
                attributeValue = ''
                typeValue = ''
                descriptionValue = ''
                mandatoryValue = ''
        elif param == 'type':
            typeValue = schema[param]
        elif param == 'enum':
            descriptionValue = 'Possible values are: ' + \
                ', '.join( ['``'+x+'``' for x in schema[param]] )
            attributeValue = 'N/A'
        elif param == 'items':
            propertyValues = schema[param]
            if '$entity_ref' in propertyValues:
                refval = propertyValues['$entity_ref']
                
                # add ref to the type
                typeValue += ' of ' + ref2link(entities, refval)
                yield '    * - N/A'
                yield '      - ' + typeValue
                yield '      - ' + descriptionValue
                yield '      - ' + mandatoryValue
        elif param == 'example':
            continue
        elif param == 'additionalProperties':
            if schema[param] is True:
                yield '    * - ...'
                yield '      - '
                yield '      - '
                yield '      - '
        elif param == '$entity_ref':
            continue
        else:
            attributeValue = schema[param]
            if isinstance(attributeValue,bool): continue
            if '$entity_ref' in attributeValue:
                attributeValue=attributeValue['$entity_ref'].replace('#/components/schemas/','')
    if(attributeValue != ''):
        yield '    * - ' + attributeValue
        yield '      - ' + typeValue
        yield '      - ' + descriptionValue
        yield '      - ' + mandatoryValue
        attributeValue = ''
        typeValue = ''
        descriptionValue = ''
        mandatoryValue = ''


def ref2link(entities, ref):
    if ref in ['object', 'string']:
        return ref
    name = ref.split('/')[-1]
    if ref[0]=='#':
        ref = ref[1:]
    ref = entities(ref)
    return ':ref:`{name} <{ref}>`'.format(**locals())


def _entities(spec, ref):
    m = hashlib.md5()
    m.update(spec['info'].get('title', '').encode('utf-8'))
    m.update(spec['info'].get('version', '0.0').encode('utf-8'))
    key = m.hexdigest()
    return key+ref


class ModelRenderer(abc.RestructuredTextRenderer):

    option_spec = {
        # prefix (components/schemas)
        # header marker (')
    }

    def __init__(self, state, options):
        self._state = state
        self._options = options

    def render_restructuredtext_markup(self, spec):

        def entities(x):
            return _entities(spec, x)


        schemas = spec['components']['schemas']
        for name,schema in schemas.items():
            for line in build_table(name, schema, entities):
                yield line






















