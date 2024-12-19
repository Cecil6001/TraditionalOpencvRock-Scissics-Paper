import cv2
import numpy as np


class HandRecognition:
    def __init__(self):
        # 优化肤色范围，使用更严格的阈值
        self.skin_ranges = [
            # YCrCb空间的肤色范围（更严格）
            {'color_space': 'YCrCb', 'ranges': [
                ((60, 135, 85), (255, 180, 135)),
            ]},
            # HSV空间的肤色范围（更严格）
            {'color_space': 'HSV', 'ranges': [
                ((0, 15, 100), (20, 170, 255)),
                ((170, 15, 100), (180, 170, 255)),
            ]},
        ]

        # 简化的手势参数
        self.gesture_params = {
            'min_area': 7000,  # 最小手部面积
            'min_solidity': 0.7,  # 最小紧凑度
            'defect_angle_range': (30, 85),  # 有效凸缺陷的角度范围
            'min_defect_depth': 12000,  # 最小凸缺陷深度
        }

    def detect_gestures(self, frame):
        """检测手势"""
        # 1. 多尺度图像预处理
        processed_mask = self._preprocess_image(frame)

        # 2. 轮廓检测和筛选
        contours, _ = cv2.findContours(processed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gestures = []

        if contours:
            # 筛选有效轮廓
            valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 5000]
            if valid_contours:
                max_contour = max(valid_contours, key=cv2.contourArea)

                # 3. 特征提取和手势识别
                features = self._extract_enhanced_features(max_contour)
                gesture = self._recognize_gesture_enhanced(features)
                gestures.append(gesture)

                # 4. 可视化
                self._draw_enhanced_feedback(frame, features, gesture, processed_mask)

        return frame, gestures

    def _preprocess_image(self, frame):
        """增强的图像预处理"""
        # 降噪和平滑
        frame = cv2.GaussianBlur(frame, (3, 3), 0)
        frame = cv2.bilateralFilter(frame, 5, 75, 75)  # 添加双边滤波

        # 创建掩码
        final_mask = np.zeros(frame.shape[:2], dtype=np.uint8)

        for color_space_info in self.skin_ranges:
            if color_space_info['color_space'] == 'YCrCb':
                converted = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            else:  # HSV
                converted = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            space_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            for lower, upper in color_space_info['ranges']:
                mask = cv2.inRange(converted, np.array(lower), np.array(upper))
                space_mask = cv2.bitwise_or(space_mask, mask)

            final_mask = cv2.bitwise_or(final_mask, space_mask)

        # 改进的形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 添加额外的噪声过滤
        final_mask = cv2.medianBlur(final_mask, 5)

        return final_mask

    def _extract_enhanced_features(self, contour):
        """增强的特征提取"""
        features = {}

        # 基本特征
        features['contour'] = contour
        features['area'] = cv2.contourArea(contour)
        features['hull'] = cv2.convexHull(contour)
        features['hull_area'] = cv2.contourArea(features['hull'])
        features['solidity'] = features['area'] / features['hull_area'] if features['hull_area'] > 0 else 0

        # 轮廓分析
        features['bbox'] = cv2.boundingRect(contour)
        features['extent'] = features['area'] / (features['bbox'][2] * features['bbox'][3])

        # 指尖检测
        features.update(self._detect_fingers(contour))

        return features

    def _detect_fingers(self, contour):
        """简化的手指检测，主要关注凸缺陷点"""
        hull = cv2.convexHull(contour, returnPoints=False)
        defects = cv2.convexityDefects(contour, hull)

        valid_defects = []
        x, y, w, h = cv2.boundingRect(contour)
        center = (x + w // 2, y + h // 2)

        # 面积检查
        area = cv2.contourArea(contour)
        if area < self.gesture_params['min_area']:
            return {
                'valid_defects': [],
                'defect_count': 0,
                'center': center,
                'bbox': (x, y, w, h)
            }

        if defects is not None:
            for i in range(defects.shape[0]):
                s, e, f, d = defects[i, 0]
                start = tuple(contour[s][0])
                end = tuple(contour[e][0])
                far = tuple(contour[f][0])

                # 计算角度
                a = np.linalg.norm(np.array(end) - np.array(start))
                b = np.linalg.norm(np.array(far) - np.array(start))
                c = np.linalg.norm(np.array(end) - np.array(far))
                angle = np.degrees(np.arccos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c)))

                # 简化的检测条件
                min_angle, max_angle = self.gesture_params['defect_angle_range']
                if (min_angle <= angle <= max_angle and
                        d > self.gesture_params['min_defect_depth'] and
                        far[1] < y + 0.8 * h):  # 确保凸缺陷点在手掌上部
                    valid_defects.append((start, end, far))

        return {
            'valid_defects': valid_defects,
            'defect_count': len(valid_defects),
            'center': center,
            'bbox': (x, y, w, h)
        }

    def _recognize_gesture_enhanced(self, features):
        """基于凸缺陷点数量的简化手势识别"""
        defect_count = features['defect_count']

        # 计算轮廓的紧凑度
        solidity = features['area'] / features['hull_area'] if features['hull_area'] > 0 else 0

        # 必须满足基本的面积和紧凑度要求
        if features['area'] < self.gesture_params['min_area'] or solidity < self.gesture_params['min_solidity']:
            return "unknown"

        # 基于凸缺陷点数量判断手势
        if defect_count == 0:
            return "rock"  # 没有凸缺陷点，说明是拳头
        elif defect_count == 1:
            return "scissors"  # 一个凸缺陷点，说明是剪刀
        elif defect_count >= 2:
            return "paper"  # 2个或更多凸缺陷点，说明是布

        return "unknown"

    def _draw_enhanced_feedback(self, frame, features, gesture, mask):
        """简化的视觉反馈"""
        # 绘制轮廓
        cv2.drawContours(frame, [features['contour']], -1, (0, 255, 0), 2)

        # 只绘制凸缺陷点（红点）
        for _, _, far in features['valid_defects']:
            cv2.circle(frame, far, 8, (0, 0, 255), -1)  # 凸缺陷点（红色）

        # 显示手势结果
        x, y, w, h = features['bbox']
        cv2.putText(frame, f"{gesture}", (x, y - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        # 显示调试信息
        debug_info = [
            f"Defects: {features['defect_count']}",
            f"Gesture: {gesture}"
        ]

        for i, text in enumerate(debug_info):
            cv2.putText(frame, text, (10, 30 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)