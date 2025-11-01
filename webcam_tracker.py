"""
Webcam-System für Hand-/Bewegungserkennung
Trackt Handbewegungen und Figuren auf dem Spieltisch
"""
import cv2
import numpy as np
import threading
import time
from collections import deque

class WebcamTracker:
    """Webcam-basiertes Tracking für Figuren und Handbewegungen"""
    
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self.thread = None
        
        # Tracking-Daten
        self.current_position = None  # Aktuelle Position (x, y)
        self.movement_vector = None   # Bewegungsvektor (dx, dy)
        self.last_positions = deque(maxlen=10)  # Letzte Positionen für Glättung
        
        # Kalibrierung
        self.table_corners = None  # Spieltisch-Ecken [top-left, top-right, bottom-right, bottom-left]
        self.map_size = (30, 20)  # Kartengröße in Tiles
        
        # Bewegungserkennung
        self.prev_frame = None
        self.motion_threshold = 500  # Mindest-Bewegung für Detektion
        
    def start(self):
        """Startet Webcam-Tracking"""
        if self.is_running:
            return
        
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            print("Fehler: Konnte Webcam nicht öffnen!")
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stoppt Webcam-Tracking"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
    
    def calibrate_table(self, corners):
        """
        Kalibriert die Spieltisch-Bereiche
        corners: Liste von 4 Punkten [(x,y), (x,y), (x,y), (x,y)]
        """
        self.table_corners = np.array(corners, dtype=np.float32)
    
    def _tracking_loop(self):
        """Haupt-Tracking-Loop (läuft in eigenem Thread)"""
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            
            # Frame verarbeiten
            self._process_frame(frame)
            
            time.sleep(0.033)  # ~30 FPS
    
    def _process_frame(self, frame):
        """Verarbeitet einen Frame für Hand-/Bewegungserkennung"""
        # Frame vorbereiten
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.prev_frame is None:
            self.prev_frame = blurred
            return
        
        # Bewegungserkennung durch Frame-Differenz
        frame_delta = cv2.absdiff(self.prev_frame, blurred)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Konturen finden
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Größte Kontur finden (wahrscheinlich Hand oder Figur)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            if area > self.motion_threshold:
                # Schwerpunkt der Bewegung berechnen
                M = cv2.moments(largest_contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Position in Karten-Koordinaten umrechnen
                    if self.table_corners is not None:
                        map_pos = self._screen_to_map(cx, cy, frame.shape)
                        if map_pos:
                            # Bewegungsvektor berechnen
                            if self.current_position:
                                dx = map_pos[0] - self.current_position[0]
                                dy = map_pos[1] - self.current_position[1]
                                self.movement_vector = (dx, dy)
                            
                            self.current_position = map_pos
                            self.last_positions.append(map_pos)
        
        self.prev_frame = blurred
    
    def _screen_to_map(self, screen_x, screen_y, frame_shape):
        """
        Konvertiert Bildschirm-Koordinaten zu Karten-Koordinaten
        """
        if self.table_corners is None:
            return None
        
        height, width = frame_shape[:2]
        
        # Perspektivische Transformation
        src_point = np.array([[screen_x, screen_y]], dtype=np.float32)
        
        # Ziel-Koordinaten (Karten-Bereich)
        dst_corners = np.array([
            [0, 0],
            [self.map_size[0], 0],
            [self.map_size[0], self.map_size[1]],
            [0, self.map_size[1]]
        ], dtype=np.float32)
        
        # Perspektiv-Matrix berechnen
        matrix = cv2.getPerspectiveTransform(self.table_corners, dst_corners)
        
        # Punkt transformieren
        transformed = cv2.perspectiveTransform(src_point.reshape(-1, 1, 2), matrix)
        
        map_x = int(transformed[0][0][0])
        map_y = int(transformed[0][0][1])
        
        # Prüfen ob im gültigen Bereich
        if 0 <= map_x < self.map_size[0] and 0 <= map_y < self.map_size[1]:
            return (map_x, map_y)
        
        return None
    
    def get_current_tile(self):
        """Gibt das aktuelle Tile zurück, auf dem Bewegung erkannt wurde"""
        if self.current_position:
            return self.current_position
        return None
    
    def get_movement_direction(self):
        """Gibt die Bewegungsrichtung zurück (normalisiert)"""
        if not self.movement_vector:
            return None
        
        dx, dy = self.movement_vector
        length = np.sqrt(dx*dx + dy*dy)
        
        if length > 0.5:  # Mindestbewegung
            return (dx / length, dy / length)
        
        return None
    
    def get_smoothed_position(self):
        """Gibt eine geglättete Position zurück (Durchschnitt der letzten Positionen)"""
        if not self.last_positions:
            return None
        
        avg_x = sum(pos[0] for pos in self.last_positions) / len(self.last_positions)
        avg_y = sum(pos[1] for pos in self.last_positions) / len(self.last_positions)
        
        return (int(avg_x), int(avg_y))
