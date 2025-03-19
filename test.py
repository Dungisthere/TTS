from transformers import AutoTokenizer, AutoModelForTextToWaveform
import torch
import soundfile as sf

# Tải tokenizer và mô hình
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
model = AutoModelForTextToWaveform.from_pretrained("facebook/mms-tts-vie")

# Văn bản tiếng Việt
text = "Trong khi JavaScript có thể chạy mô hình AI thông qua các thư viện như TensorFlow.js hoặc ONNX.js, các mô hình này sẽ không thể tận dụng tối đa phần cứng (GPU) như trong Python. Python, nhờ vào các thư viện như torch và tensorflow, có thể tận dụng tối đa hiệu suất phần cứng để thực hiện các tác vụ tính toán nặng, đặc biệt trong môi trường server hoặc môi trường cloud."

# Tokenize văn bản
inputs = tokenizer(text, return_tensors="pt")  # "pt" là PyTorch

# Tạo âm thanh
with torch.no_grad():
    output = model(**inputs).waveform

# Chuyển đổi và lưu file âm thanh
audio = output.squeeze().cpu().numpy()  # Chuyển tensor thành mảng numpy
sampling_rate = model.config.sampling_rate  # Lấy tần số mẫu từ config
sf.write("xin_chao.wav", audio, sampling_rate)
print("Đã tạo file xin_chao.wav")