from config.dnn_config import ModelConfiguration
import os
import time
import cv2 as cv
import numpy as np

# Constants.
INPUT_WIDTH = 640
INPUT_HEIGHT = 640
SCORE_THRESHOLD = 0.2
NMS_THRESHOLD = 0.4
CONFIDENCE_THRESHOLD = 0.4

# Text parameters.
FONT_FACE = cv.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.5
THICKNESS = 1

# Colors
BLACK = (0, 0, 0)
BLUE = (255, 178, 50)
YELLOW = (0, 255, 255)
RED = (0, 0, 255)
WHITE = (255, 0, 127)

# Create folder for saving video
destination_video_dir = "./yolov5_videos_with_inference/"
os.makedirs(destination_video_dir, exist_ok=True)

class Detection:
    """Object initialization"""
    def __init__(self, network, label):
        self.network = network
        self.label = label

    def pre_process(self, input_image, net):
        # Create a 4D blob from a frame.
        blob = cv.dnn.blobFromImage(input_image, 1 / 255.0, (INPUT_WIDTH, INPUT_HEIGHT), swapRB=True, crop=False)

        # Sets the input to the network.
        net.setInput(blob)

        # Runs the forward pass to get output of the output layers.
        output_layers = net.getUnconnectedOutLayersNames()

        output = net.forward(output_layers)
        # print(outputs[0].shape)
        return output

    def post_process(self, input_image, outputs, labels):
        # Lists to hold respective values while unwrapping.
        class_ids = []
        confidences = []
        boxes = []

        # Rows.
        rows = outputs[0].shape[1]

        image_height, image_width = input_image.shape[:2]

        # Resizing factor.
        x_factor = image_width / INPUT_WIDTH
        y_factor = image_height / INPUT_HEIGHT

        # Iterate through 25200 detections.
        for r in range(rows):
            row = outputs[0][0][r]
            confidence = row[4]

            # Discard bad detections and continue.
            if confidence >= CONFIDENCE_THRESHOLD:
                classes_scores = row[5:]

                # Get the index of max class score.
                class_id = np.argmax(classes_scores)

                #  Continue if the class score is above threshold.
                if classes_scores[class_id] > SCORE_THRESHOLD:
                    confidences.append(confidence)
                    class_ids.append(class_id)

                    cx, cy, w, h = row[0], row[1], row[2], row[3]

                    left = int((cx - w / 2) * x_factor)
                    top = int((cy - h / 2) * y_factor)
                    width = int(w * x_factor)
                    height = int(h * y_factor)

                    box = np.array([left, top, width, height])
                    boxes.append(box)

        # Perform non-maximum suppression to eliminate redundant overlapping boxes with
        # lower confidences.
        indices = cv.dnn.NMSBoxes(boxes, confidences, CONFIDENCE_THRESHOLD, NMS_THRESHOLD)
        for i in indices:
            box = boxes[i]
            left = box[0]
            top = box[1]
            width = box[2]
            height = box[3]
            cv.rectangle(input_image, (left, top), (left + width, top + height), BLUE, 2 * THICKNESS)
            label = "{}:{:.2f}".format(labels[class_ids[i]], confidences[i])
            self.draw_label(input_image, label, left, top)

        return input_image

    def draw_label(self, input_image, label, left, top):
        """Draw text onto image at location."""

        # Get text size.
        text_size = cv.getTextSize(label, FONT_FACE, FONT_SCALE, THICKNESS)
        dim, baseline = text_size[0], text_size[1]
        # Use text size to create a BLACK rectangle.
        cv.rectangle(input_image, (left, top - 20), (left + dim[0], top + dim[1] + baseline - 20), BLACK, cv.FILLED)
        # Display text inside the rectangle.
        cv.putText(input_image, label, (left, top + dim[1] - 20), FONT_FACE, FONT_SCALE, YELLOW, THICKNESS, cv.LINE_AA)

    def read_label(self):
        # label name
        lines = []
        with open(self.label) as f:
            for line in f:
                lines.append(line.rstrip())
        return lines

    def write_fps(self, file):
        file = destination_video_dir + 'v5_write_fps.txt'
        # delete previous file
        if os.path.exists(file):
            os.remove(file)
            # create new file
            f = open(file, "x")
            f.close()

if __name__ == "__main__":
    # Load network
    model_name = './models/iteration_10_v5_best.onnx'
    label_file = 'classes.txt'
    fps_file = destination_video_dir + 'v5_write_fps.txt'

    model = ModelConfiguration(model_name)
    net = model.modelConfig("YOLOV5")

    if net is not None:
        Inspection = Detection(net, label_file)
        Inspection.write_fps(fps_file)
        capture = cv.VideoCapture("propeller_3.mp4")
        # capture = cv.VideoCapture(1)

        start = time.time_ns()
        frame_count = 0
        total_frames = 0
        fps = -1

        if capture.isOpened():
            # camera_frame_width = int(capture.get(3))
            # camera_frame_height = int(capture.get(4))
            frame_width = 700
            frame_height = 700
            print("frame width : ", frame_width)
            print("frame height : ", frame_height)
            size = (frame_width, frame_height)

            result = cv.VideoWriter(destination_video_dir + 'yolov5_output_cpu_core_i5.avi', cv.VideoWriter_fourcc(*'XVID'), 20.0, size)

            while True:
                ret, frame = capture.read()
                if frame is None:
                    print("End of stream")
                    break
                outputs = Inspection.pre_process(frame, net)
                classes = Inspection.read_label()

                if ret:
                    frame_count += 1
                    total_frames += 1
                    frame = cv.resize(frame, size, fx=0, fy=0, interpolation=cv.INTER_AREA)
                    img = Inspection.post_process(frame, outputs, classes)

                    #if frame_count >= 5:
                    end = time.time_ns()
                    fps = 1000000000 * frame_count / (end - start)
                    frame_count = 0
                    start = time.time_ns()

                    if fps > 0:
                        fps_label = "FPS: %.2f" % fps
                        cv.putText(img, fps_label, (10, 25), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        f = open(fps_file, "a+")
                        f.write('%f\n' % fps )
                        f.close()

                    cv.imshow('Propeller fault detection (CPU: Core i5)', img)
                    result.write(img)

                    # key: 'ESC'
                    key = cv.waitKey(20)
                    if key == 27:
                        break
                else:
                    break

                print("Total frames: " + str(total_frames))
        else:
            print("Please check the video file name")

        capture.release()
        result.release()
        cv.destroyAllWindows()
    else:
        print("Please check network Configuration")

