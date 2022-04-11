from flask_restplus import reqparse, inputs
#import werkzeug

#text_input = reqparse.RequestParser()
#text_input.add_argument('input_text', type=str,  location='form')
#file_input = reqparse.RequestParser()
#file_input.add_argument('input_text', type=werkzeug.datastructures.FileStorage, location='files')
text_input_with_src_tgt = reqparse.RequestParser()
text_input_with_src_tgt.add_argument('input_text', type=str,  location='form')
text_input_with_src_tgt.add_argument('src', type=str)
text_input_with_src_tgt.add_argument('tgt', type=str)
text_input_with_src_tgt.add_argument('author', type=str)
text_input_with_src_tgt.add_argument('frontend', type=str)
text_input_with_src_tgt.add_argument('X-Frontend', type=str, location='headers')
text_input_with_src_tgt.add_argument('X-App-Version', type=str, location='headers')
text_input_with_src_tgt.add_argument('X-User-Language', type=str, location='headers')
text_input_with_src_tgt.add_argument('inputType', type=str)
text_input_with_src_tgt.add_argument('logInput', type=inputs.boolean)
