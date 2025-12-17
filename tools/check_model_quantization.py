import openvino as ov
import os

import argparse

parser = argparse.ArgumentParser(prog='check model quantization parameters')
parser.add_argument('-i', '--input', help='input path to the model')


# parser.print_help()
args = parser.parse_args()
print("args: ", args)

model_path = "./openvino_model.xml"

if os.path.exists(args.input):
    model_path = args.input



def identify_quantization_scheme(model_path):
    """Identify the quantization scheme of your model"""
    core = ov.Core()
    model = core.read_model(model_path)
    
    # Look for quantization patterns
    weight_precisions = set()
    activation_precisions = set()
    
    for op in model.get_ops():
        op_name = op.get_friendly_name()
        
        # Check if it's a weight operation (Constant nodes)
        if "Constant" in op.get_type_name():
            precision = str(op.get_output_element_type(0))
            weight_precisions.add(precision)
        else:
            # Likely activation-related
            for output in op.outputs():
                precision = str(output.get_element_type())
                activation_precisions.add(precision)
    
    print(f"Detected Weight Precisions: {weight_precisions}")
    print(f"Detected Activation Precisions: {activation_precisions}")
    
    # Make educated guess about scheme
    if "i4" in weight_precisions and "f16" in activation_precisions:
        return "FP16A + INT4W"
    elif "i8" in weight_precisions and "i8" in activation_precisions:
        return "A8W8"
    elif "i4" in weight_precisions and "i8" in activation_precisions:
        return "A8W4"
    else:
        return "Mixed/Unknown"

# Check your model
scheme = identify_quantization_scheme(model_path)
print(f"Quantization Scheme: {scheme}")