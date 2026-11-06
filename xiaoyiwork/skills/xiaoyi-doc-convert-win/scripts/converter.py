"""
Document converter - main conversion dispatcher.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional, List, Dict

from routing import find_conversion_path, normalize_format, is_conversion_supported
from adapters import OfficeComAdapter, SofficeAdapter


def available_output_path(output_dir: Path, filename: str) -> Path:
    target = output_dir / filename
    index = 2
    while target.exists():
        target = output_dir / f"{Path(filename).stem} ({index}){Path(filename).suffix}"
        index += 1
    return target


class DocumentConverter:
    """Main document converter that orchestrates conversions."""

    def __init__(self):
        # Initialize all adapters
        self.adapters = {
            'office-com': OfficeComAdapter(),
            'soffice': SofficeAdapter(),
        }

    def check_adapter(self, name: str) -> tuple[bool, str]:
        """Check if an adapter is available."""
        if name not in self.adapters:
            return False, f"Unknown adapter: {name}"
        return self.adapters[name].check_dependencies()

    def convert(self, input_path: str, target_format: str, output_path: Optional[str] = None,
                **kwargs) -> str:
        """
        Convert a document to the target format.

        Args:
            input_path: Path to input file
            target_format: Target format (e.g., 'pdf', 'docx', 'pptx')
            output_path: Optional output path (default: current task workspace, new extension)
            **kwargs: Additional conversion options

        Returns:
            Path to the output file

        Raises:
            ValueError: If conversion is not supported
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If conversion fails
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Determine source format from file extension
        source_format = input_path.suffix.lstrip('.')

        # Normalize target format
        target_format = normalize_format(target_format)

        # Find conversion path
        path = find_conversion_path(source_format, target_format)

        if not path:
            raise ValueError(
                f"Conversion from {source_format} to {target_format} is not supported. "
                f"Use '--list' to see supported conversions."
            )

        # Determine output path if not provided
        if not output_path:
            output_path = available_output_path(Path.cwd(), f"{input_path.stem}.{target_format}")
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Execute conversion(s)
        current_file = str(input_path)
        intermediate_files = []
        temp_dirs = []

        try:
            for step in path:
                adapter_name = step['adapter']
                from_fmt = step['from']
                to_fmt = step['to']

                # Check if this is the final step
                is_final = (step == path[-1])

                if is_final:
                    # Final step outputs to the desired output path
                    step_output = str(output_path)
                else:
                    # Intermediate step - use temp file
                    temp_dir = Path(tempfile.mkdtemp(prefix="docconv_"))
                    step_output = str(temp_dir / f"intermediate.{to_fmt}")
                    intermediate_files.append(step_output)
                    temp_dirs.append(temp_dir)

                if adapter_name == 'html2pdf':
                    import html2pdf.core as html2pdf_core
                    html2pdf_core.html_to_pdf(
                        current_file, step_output,
                        page_width=kwargs.get('width'),
                        page_height=kwargs.get('height')
                    )
                elif adapter_name == 'md2doc':
                    import md2doc.converter as md2doc_converter
                    md2doc_converter.convert_markdown(
                        current_file, step_output, to_fmt,
                        device_type=kwargs.get('device_type', 'pc')
                    )
                elif adapter_name == 'html2md':
                    import importlib.util
                    html2md_path = os.path.join(os.path.dirname(__file__), 'md2doc', 'utils', 'html2md.py')
                    spec = importlib.util.spec_from_file_location('html2md', html2md_path)
                    html2md_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(html2md_module)
                    html_to_markdown = html2md_module.html_to_markdown
                    try:
                        with open(current_file, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        md_content = html_to_markdown(html_content)
                        with open(step_output, 'w', encoding='utf-8') as f:
                            f.write(md_content)
                    except (OSError, UnicodeDecodeError) as e:
                        raise RuntimeError(f"html2md conversion failed: {e}")
                elif adapter_name == 'soffice':
                    errors = []
                    converted = False
                    office = self.adapters['office-com']
                    if office.supports(from_fmt, to_fmt):
                        office_available, office_error = office.check_dependencies(from_fmt, to_fmt)
                        if office_available:
                            try:
                                converted = office.convert(current_file, step_output, **kwargs)
                                if converted:
                                    print(f"Conversion backend: Microsoft Office ({from_fmt} -> {to_fmt})")
                            except Exception as exc:
                                errors.append(f"Microsoft Office: {exc}")
                        else:
                            errors.append(f"Microsoft Office: {office_error}")

                    if not converted:
                        # Office 失败时可能留下不完整产物，避免影响回退后端。
                        try:
                            Path(step_output).unlink(missing_ok=True)
                        except OSError:
                            pass
                        # 这个预处理会删除高密度空 shape，仅用于规避 soffice
                        # 超时；Microsoft Office 后端必须使用原始 PPTX。
                        soffice_input = current_file
                        if from_fmt == 'pptx' and to_fmt == 'pdf':
                            try:
                                from ppt.utils import preprocess_pptx_for_pdf
                                temp_dir = Path(tempfile.mkdtemp(prefix="docconv_pptx_"))
                                temp_pptx = str(temp_dir / "preprocessed.pptx")
                                if preprocess_pptx_for_pdf(current_file, temp_pptx):
                                    soffice_input = temp_pptx
                                    intermediate_files.append(temp_pptx)
                                    temp_dirs.append(temp_dir)
                                else:
                                    shutil.rmtree(temp_dir, ignore_errors=True)
                            except Exception as e:
                                print(f"PPTX preprocessing skipped: {e}")

                        soffice = self.adapters['soffice']
                        soffice_available, soffice_error = soffice.check_dependencies()
                        if soffice_available:
                            try:
                                converted = soffice.convert(soffice_input, step_output, **kwargs)
                                if converted:
                                    print(f"Conversion backend: LibreOffice ({from_fmt} -> {to_fmt})")
                            except Exception as exc:
                                errors.append(f"LibreOffice: {exc}")
                        else:
                            errors.append(f"LibreOffice: {soffice_error}")

                    if not converted:
                        detail = '; '.join(errors) or 'no compatible conversion backend'
                        raise RuntimeError(
                            f"No available Office conversion backend for {from_fmt} -> {to_fmt}: {detail}"
                        )
                else:
                    raise RuntimeError(f"Unknown adapter: {adapter_name}")

                # Update current file for next step
                current_file = step_output

            return str(output_path)

        finally:
            # Cleanup intermediate files
            for f in intermediate_files:
                try:
                    f_path = Path(f)
                    if f_path.exists():
                        f_path.unlink()
                except Exception:
                    pass  # Ignore cleanup errors

            # Cleanup temp directories
            for d in temp_dirs:
                try:
                    if d.exists():
                        shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass  # Ignore cleanup errors

    def get_supported_conversions(self) -> Dict[str, List[str]]:
        """Get dictionary of supported conversions."""
        from routing import get_conversion_matrix
        return get_conversion_matrix()


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
