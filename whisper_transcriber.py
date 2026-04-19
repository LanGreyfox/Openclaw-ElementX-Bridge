"""
Whisper Fast Transcription Module

This module provides a class for fast audio transcription
using Whisper Fast (faster-whisper).
"""

from faster_whisper import WhisperModel
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    A class for audio transcription using Whisper Fast.
    
    This class uses the faster-whisper model for fast and efficient
    transcription of audio files to text.
    
    Attributes:
        model_size (str): Size of the Whisper model ('tiny', 'base', 'small', 'medium', 'large')
        device (str): Device to run on ('cpu' or 'cuda')
        compute_type (str): Computation type ('int8', 'int8_float16', 'int16', 'float16', 'float32')
        model (WhisperModel): The loaded Whisper model
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8"
    ):
        """
        Initializes the Whisper Transcriber.
        
        Args:
            model_size: Model size. Options: 'tiny', 'base', 'small', 'medium', 'large'
                       (larger = better accuracy but slower)
            device: 'cpu' or 'cuda' (for GPU acceleration)
            compute_type: Computation type for optimization
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        
        logger.info(
            f"Loading Whisper model: {model_size} "
            f"(Device: {device}, Compute: {compute_type})"
        )
        
        self.model = WhisperModel(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type
        )
        
        logger.info("Whisper model loaded successfully")
    
    def transcribe(
        self,
        audio_path: str,
        language: str = None,
        task: str = "transcribe"
    ) -> dict:
        """
        Transcribes an audio file to text.
        
        Args:
            audio_path: Path to the audio file
            language: Language as 2-letter code (e.g. 'de' for German, 'en' for English)
                     If None, language will be auto-detected
            task: 'transcribe' for transcription, 'translate' for translation to English
        
        Returns:
            dict: Dictionary with the following structure:
                {
                    'text': str,           # The complete transcribed text
                    'segments': list,      # List of segments with timings
                    'language': str        # Detected/used language
                }
        
        Raises:
            FileNotFoundError: If the audio file does not exist
            ValueError: If task is not 'transcribe' or 'translate'
        """
        # Check if file exists
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Validate task parameter
        if task not in ["transcribe", "translate"]:
            raise ValueError(f"task must be 'transcribe' or 'translate', not '{task}'")
        
        logger.info(f"Starting transcription: {audio_file.name}")
        
        try:
            # Perform transcription
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                task=task
            )
            
            # Convert segments to list and collect text
            segments_list = []
            full_text = []
            
            for segment in segments:
                segment_data = {
                    'id': segment.id,
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                    'confidence': segment.avg_logprob if hasattr(segment, 'avg_logprob') else None
                }
                segments_list.append(segment_data)
                full_text.append(segment.text)
            
            result = {
                'text': ' '.join(full_text).strip(),
                'segments': segments_list,
                'language': info.language,
                'language_probability': info.language_probability if hasattr(info, 'language_probability') else None
            }
            
            logger.info(
                f"Transcription completed. "
                f"Language: {info.language}, "
                f"Segments: {len(segments_list)}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            raise
    
    def transcribe_with_timestamps(
        self,
        audio_path: str,
        language: str = None
    ) -> list:
        """
        Transcribes an audio file and returns segments with precise timestamps.
        
        Args:
            audio_path: Path to the audio file
            language: Language as 2-letter code
        
        Returns:
            list: List of segments with format:
                [
                    {'start': 0.5, 'end': 2.3, 'text': '...'},
                    ...
                ]
        """
        result = self.transcribe(audio_path, language=language)
        return result['segments']
    
    def transcribe_and_get_text(
        self,
        audio_path: str,
        language: str = None
    ) -> str:
        """
        Transcribes an audio file and returns only the text.
        
        Args:
            audio_path: Path to the audio file
            language: Language as 2-letter code
        
        Returns:
            str: The transcribed text
        """
        result = self.transcribe(audio_path, language=language)
        return result['text']
