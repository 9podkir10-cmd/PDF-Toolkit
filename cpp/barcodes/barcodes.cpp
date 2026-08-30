#include <mupdf/fitz.h>
#include <mupdf/pdf.h>
#include <opencv2/opencv.hpp>
#include <zbar.h>
#include <iostream>
#include <filesystem>
#include <string>
#include <vector>
#include <cwctype>
#include <algorithm>
#include <windows.h>
#include <fcntl.h>
#include <io.h>
#include <chrono>
#include <thread>
#include <cstdlib>

namespace fs = std::filesystem;

cv::Mat render_page_rgb(fz_context* ctx, fz_page* page, float zoom = 1.5f) {
    fz_rect bounds = fz_bound_page(ctx, page);
    fz_matrix ctm = fz_scale(zoom, zoom);
    fz_rect transformed = fz_transform_rect(bounds, ctm);
    int w = static_cast<int>(transformed.x1 - transformed.x0);
    int h = static_cast<int>(transformed.y1 - transformed.y0);
    
    fz_pixmap* pix = fz_new_pixmap(ctx, fz_device_rgb(ctx), w, h, nullptr, 0);
    if (!pix) {
        std::wcerr << L"  [ERROR] Failed to create pixmap\n";
        return cv::Mat();
    }
    fz_clear_pixmap_with_value(ctx, pix, 0xFF);
    fz_device* dev = fz_new_draw_device(ctx, ctm, pix);
    if (!dev) {
        std::wcerr << L"  [ERROR] Failed to create draw device\n";
        fz_drop_pixmap(ctx, pix);
        return cv::Mat();
    }
    
    fz_try(ctx) {
        fz_run_page(ctx, page, dev, fz_identity, nullptr);
    } fz_catch(ctx) {
        std::wcerr << L"  [ERROR] MuPDF exception during page rendering\n";
        fz_drop_device(ctx, dev);
        fz_drop_pixmap(ctx, pix);
        return cv::Mat();
    }

    fz_close_device(ctx, dev);
    fz_drop_device(ctx, dev);

    cv::Mat img(h, w, CV_8UC3, pix->samples, pix->stride);
    cv::Mat img_copy = img.clone();
    fz_drop_pixmap(ctx, pix);
    return img_copy;
}

std::wstring utf8_to_wstring(const std::string& str) {
    if (str.empty()) return {};
    int wlen = MultiByteToWideChar(CP_UTF8, 0, str.c_str(), -1, nullptr, 0);
    if (wlen == 0) return {};
    std::wstring wstr(wlen, L'\0');
    MultiByteToWideChar(CP_UTF8, 0, str.c_str(), -1, &wstr[0], wlen);
    if (!wstr.empty() && wstr.back() == L'\0') wstr.pop_back();
    return wstr;
}

std::string wstring_to_utf8(const std::wstring& wstr) {
    if (wstr.empty()) return {};
    int len = WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), -1, nullptr, 0, nullptr, nullptr);
    if (len == 0) return {};
    std::string utf8_str(len, '\0');
    WideCharToMultiByte(CP_UTF8, 0, wstr.c_str(), -1, &utf8_str[0], len, nullptr, nullptr);
    if (!utf8_str.empty() && utf8_str.back() == '\0') utf8_str.pop_back();
    return utf8_str;
}

std::string clean_barcode_data(const std::string& decoded) {
    std::string cleaned = decoded;
    std::transform(cleaned.begin(), cleaned.end(), cleaned.begin(),
                   [](unsigned char c){ return std::toupper(c); });
    std::string allowed_chars = "PATCHT1234";
    cleaned.erase(std::remove_if(cleaned.begin(), cleaned.end(),
                                 [&allowed_chars](char c) {
                                     return allowed_chars.find(c) == std::string::npos;
                                 }),
                  cleaned.end());
    return cleaned;
}

bool detect_barcode(const cv::Mat& gray, const std::vector<std::string>& target_patterns) {
    if (gray.empty() || gray.type() != CV_8UC1) return false;

    zbar::ImageScanner scanner;
    scanner.set_config(zbar::ZBAR_NONE, zbar::ZBAR_CFG_ENABLE, 0);
    scanner.set_config(zbar::ZBAR_CODE39, zbar::ZBAR_CFG_ENABLE, 1);
    scanner.enable_cache(false);

    zbar::Image zbar_img(gray.cols, gray.rows, "Y800", gray.data, static_cast<unsigned long>(gray.total()));
    int scan_result = scanner.scan(zbar_img);

    if (scan_result <= 0) {
        return false;
    }

    for (auto symbol = zbar_img.symbol_begin(); symbol != zbar_img.symbol_end(); ++symbol) {
        if (symbol->get_type() != zbar::ZBAR_CODE39) continue;

        std::string decoded = symbol->get_data();
        std::string cleaned = clean_barcode_data(decoded);

        std::wcout << L"  [DEBUG] Decoded: '" << utf8_to_wstring(cleaned) << L"'" << std::endl;

        for (const auto& pattern : target_patterns) {
            if (cleaned == pattern) {
                return true;
            }
        }
    }
    return false;
}

bool save_buffer_unicode(
    fz_context* ctx,
    fz_buffer* buffer,
    const fs::path& output_path)
{
    if (!buffer) {
        std::wcerr << L"ERROR: buffer is null\n";
        return false;
    }

    unsigned char* data = nullptr;
    size_t size = fz_buffer_storage(ctx, buffer, &data);

    if (!data || size == 0) {
        std::wcerr << L"ERROR: PDF buffer is empty for:\n"
                   << L"[" << output_path.wstring() << L"]\n";
        return false;
    }

    std::wstring filename = output_path.wstring();

    HANDLE hFile = CreateFileW(
        filename.c_str(),
        GENERIC_WRITE,
        0,
        nullptr,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );

    if (hFile == INVALID_HANDLE_VALUE) {
        DWORD error = GetLastError();
        std::wcerr << L"ERROR: Cannot create output file:\n"
                   << L"[" << filename << L"]\n"
                   << L"Windows error: " << error << L"\n";
        return false;
    }

    size_t total_written = 0;
    while (total_written < size) {
        DWORD chunk_size = static_cast<DWORD>(
            (std::min)(size - total_written, static_cast<size_t>(1024 * 1024))
        );
        DWORD written = 0;
        BOOL ok = WriteFile(hFile, data + total_written, chunk_size, &written, nullptr);
        if (!ok) {
            DWORD error = GetLastError();
            CloseHandle(hFile);
            std::wcerr << L"ERROR: WriteFile failed:\n"
                       << L"[" << filename << L"]\n"
                       << L"Windows error: " << error << L"\n";
            return false;
        }
        if (written == 0) {
            CloseHandle(hFile);
            std::wcerr << L"ERROR: WriteFile wrote 0 bytes:\n"
                       << L"[" << filename << L"]\n";
            return false;
        }
        total_written += written;
    }

    CloseHandle(hFile);

    std::error_code ec;
    bool exists = fs::exists(output_path, ec);
    if (ec || !exists) {
        std::wcerr << L"ERROR: Output file was not created:\n"
                   << L"[" << filename << L"]\n";
        return false;
    }
    uintmax_t file_size = fs::file_size(output_path, ec);
    if (ec || file_size == 0) {
        std::wcerr << L"ERROR: Output file is empty:\n"
                   << L"[" << filename << L"]\n";
        return false;
    }

    std::wcout << L"  Created: " << filename << L" (" << file_size << L" bytes)\n";
    return true;
}

std::vector<std::wstring> split_pdf_by_code39(
    const fs::path& pdf_path,
    const std::vector<int>& barcode_pages,
    const fs::path& output_dir = fs::path()
) {
    std::vector<std::wstring> created_files;

    if (barcode_pages.empty())
        return created_files;

    fs::path out_dir = output_dir;
    if (out_dir.empty()) {
        out_dir = pdf_path.parent_path() / (pdf_path.stem().wstring() + L"_split");
    }

    std::error_code dir_ec;
    fs::create_directories(out_dir, dir_ec);
    if (dir_ec) {
        std::wcerr << L"ERROR: Cannot create output directory:\n"
                   << L"[" << out_dir.wstring() << L"]\n"
                   << L"Error: " << utf8_to_wstring(dir_ec.message()) << L"\n";
        return created_files;
    }

    std::wcout << L"Output directory:\n[" << out_dir.wstring() << L"]\n";

    fz_context* ctx = fz_new_context(nullptr, nullptr, FZ_STORE_DEFAULT);
    if (!ctx) {
        std::wcerr << L"ERROR: Failed to create MuPDF context\n";
        return created_files;
    }
    fz_register_document_handlers(ctx);

    std::wstring source_path = pdf_path.wstring();
    fz_stream* stream = fz_open_file_w(ctx, source_path.c_str());
    if (!stream) {
        std::wcerr << L"ERROR: Cannot open source PDF:\n"
                   << L"[" << source_path << L"]\n";
        fz_drop_context(ctx);
        return created_files;
    }

    fz_document* src_doc = fz_open_document_with_stream(ctx, "pdf", stream);
    if (!src_doc) {
        std::wcerr << L"ERROR: Cannot open PDF document\n";
        fz_drop_stream(ctx, stream);
        fz_drop_context(ctx);
        return created_files;
    }

    int total_pages = fz_count_pages(ctx, src_doc);
    std::wcout << L"Total pages: " << total_pages << L"\n";

    std::vector<int> separators = barcode_pages;
    std::sort(separators.begin(), separators.end());
    separators.erase(std::unique(separators.begin(), separators.end()), separators.end());

    separators.erase(
        std::remove_if(separators.begin(), separators.end(),
                       [total_pages](int page) { return page < 0 || page >= total_pages; }),
        separators.end()
    );

    if (separators.empty()) {
        std::wcerr << L"ERROR: No valid barcode pages\n";
        fz_drop_document(ctx, src_doc);
        fz_drop_context(ctx);
        return created_files;
    }

    struct PageRange { int first; int last; };
    std::vector<PageRange> ranges;
    int start_page = 0;

    for (int separator : separators) {
        if (separator > start_page) {
            ranges.push_back({start_page, separator - 1});
        }
        start_page = separator + 1;
    }
    if (start_page < total_pages) {
        ranges.push_back({start_page, total_pages - 1});
    }

    std::wcout << L"Parts to create: " << ranges.size() << L"\n";

    int part_number = 1;
    for (const PageRange& range : ranges) {
        if (range.first > range.last) continue;

        std::wstring filename = pdf_path.stem().wstring() + L"_part" + std::to_wstring(part_number) + L".pdf";
        fs::path out_path = out_dir / filename;

        std::wcout << L"\nCreating part " << part_number
                   << L": pages " << (range.first + 1) << L"-" << (range.last + 1) << L"\n";
        std::wcout << L"Output:\n[" << out_path.wstring() << L"]\n";

        fz_buffer* buffer = fz_new_buffer(ctx, 1024);
        if (!buffer) {
            std::wcerr << L"ERROR: Failed to create PDF buffer\n";
            break;
        }

        fz_document_writer* writer = fz_new_document_writer_with_buffer(ctx, buffer, "pdf", nullptr);
        if (!writer) {
            std::wcerr << L"ERROR: Failed to create PDF writer\n";
            fz_drop_buffer(ctx, buffer);
            break;
        }

        bool page_error = false;
        for (int page_num = range.first; page_num <= range.last; ++page_num) {
            fz_page* page = fz_load_page(ctx, src_doc, page_num);
            if (!page) {
                std::wcerr << L"ERROR: Failed to load page " << (page_num + 1) << L"\n";
                page_error = true;
                continue;
            }

            fz_rect mediabox = fz_bound_page(ctx, page);
            fz_device* device = fz_begin_page(ctx, writer, mediabox);
            if (!device) {
                std::wcerr << L"ERROR: Failed to create PDF page device for page " << (page_num + 1) << L"\n";
                fz_drop_page(ctx, page);
                page_error = true;
                continue;
            }

            fz_run_page(ctx, page, device, fz_identity, nullptr);
            fz_end_page(ctx, writer);
            fz_drop_page(ctx, page);
        }

        fz_close_document_writer(ctx, writer);
        fz_drop_document_writer(ctx, writer);

        if (page_error) {
            std::wcerr << L"WARNING: Some pages could not be copied to part " << part_number << L"\n";
        }

        unsigned char* data = nullptr;
        size_t data_size = fz_buffer_storage(ctx, buffer, &data);
        std::wcout << L"Generated PDF size: " << data_size << L" bytes\n";

        if (!data || data_size == 0) {
            std::wcerr << L"ERROR: Generated PDF is empty\n";
            fz_drop_buffer(ctx, buffer);
            break;
        }

        bool saved = save_buffer_unicode(ctx, buffer, out_path);
        fz_drop_buffer(ctx, buffer);

        if (!saved) {
            std::wcerr << L"ERROR: Failed to save part " << part_number << L"\n";
            break;
        }

        created_files.push_back(out_path.wstring());
        ++part_number;
    }

    fz_drop_document(ctx, src_doc);
    fz_drop_context(ctx);

    return created_files;
}

void process_pdf(
    const fs::path& pdf_path,
    const std::vector<std::string>& patterns,
    const fs::path& output_dir = fs::path()
) {
    std::wcout << L"\nProcessing: " << pdf_path.wstring() << std::endl;

    fz_context* ctx = fz_new_context(nullptr, nullptr, FZ_STORE_DEFAULT);
    if (!ctx) {
        std::wcerr << L"Failed to create MuPDF context" << std::endl;
        return;
    }
    fz_register_document_handlers(ctx);

    // Шаг 1
    std::wcout << L"  [1] Opening file..." << std::endl;
    fz_stream* stream = nullptr;
    fz_try(ctx) {
        stream = fz_open_file_w(ctx, pdf_path.wstring().c_str());
    } fz_catch(ctx) {
        std::wcerr << L"  [ERROR] fz_open_file_w exception for " << pdf_path.wstring() << std::endl;
        fz_drop_context(ctx);
        return;
    }

    std::wcout << L"  [2] File opened successfully" << std::endl;

    if (!stream) {
        std::wcerr << L"  [ERROR] stream == nullptr" << std::endl;
        fz_drop_context(ctx);
        return;
    }

    std::wcout << L"  [3] Opening PDF document..." << std::endl;

    fz_document* doc = nullptr;
    fz_try(ctx) {
        doc = fz_open_document_with_stream(ctx, "pdf", stream);
    } fz_catch(ctx) {
        std::wcerr << L"  [ERROR] fz_open_document_with_stream exception" << std::endl;
        fz_drop_stream(ctx, stream);
        fz_drop_context(ctx);
        return;
    }

    std::wcout << L"  [4] PDF document opened successfully" << std::endl;

    if (!doc) {
        std::wcerr << L"  [ERROR] doc == nullptr" << std::endl;
        fz_drop_stream(ctx, stream);
        fz_drop_context(ctx);
        return;
    }

    std::wcout << L"  [5] Counting pages..." << std::endl;

    int page_count = 0;
    fz_try(ctx) {
        page_count = fz_count_pages(ctx, doc);
    } fz_catch(ctx) {
        std::wcerr << L"  [ERROR] fz_count_pages exception" << std::endl;
        fz_drop_document(ctx, doc);
        fz_drop_stream(ctx, stream);
        fz_drop_context(ctx);
        return;
    }

    std::wcout << L"  [6] Pages: " << page_count << std::endl;

    std::vector<int> found_pages;

    for (int i = 0; i < page_count; ++i) {
        std::wcout << L"  Processing page " << i << L" ..." << std::flush;

        fz_page* page = nullptr;
        fz_try(ctx) {
            page = fz_load_page(ctx, doc, i);
        } fz_catch(ctx) {
            std::wcerr << L" [ERROR] Failed to load page " << i << L" (MuPDF exception)" << std::endl;
            continue;
        }

        if (!page) {
            std::wcerr << L" [ERROR] Failed to load page " << i << std::endl;
            continue;
        }

        cv::Mat rgb;
        fz_try(ctx) {
            rgb = render_page_rgb(ctx, page, 2.0f);
        } fz_catch(ctx) {
            std::wcerr << L" [ERROR] MuPDF exception during render_page_rgb for page " << i << std::endl;
            fz_drop_page(ctx, page);
            continue;
        }

        fz_drop_page(ctx, page);

        if (rgb.empty()) {
            std::wcerr << L" [WARN] Render returned empty for page " << i << std::endl;
            continue;
        }

        cv::Mat gray;
        cv::cvtColor(rgb, gray, cv::COLOR_RGB2GRAY);
        rgb.release();

        bool found = false;
        try {
            found = detect_barcode(gray, patterns);
        } catch (const std::exception& e) {
            std::wcerr << L" [ERROR] detect_barcode threw exception: " << utf8_to_wstring(e.what()) << std::endl;
            continue;
        }

        if (found) {
            found_pages.push_back(i);
            std::wcout << L" >>> Barcode found on page " << i << std::endl;
        } else {
            std::wcout << L" no barcode" << std::endl;
        }
    }

    fz_drop_document(ctx, doc);
    fz_drop_stream(ctx, stream);
    fz_drop_context(ctx);

    if (found_pages.empty()) {
        std::wcout << L"No barcodes found in " << pdf_path.wstring() << std::endl;
        return;
    }

    std::wcout << L"Found on pages: ";
    for (size_t j = 0; j < found_pages.size(); ++j) {
        std::wcout << found_pages[j] << (j + 1 < found_pages.size() ? L", " : L"");
    }
    std::wcout << std::endl;

    std::wcout << L"Splitting PDF..." << std::endl;
    std::vector<std::wstring> created_files = split_pdf_by_code39(pdf_path, found_pages, output_dir);
    std::wcout << L"Split complete. Created " << created_files.size() << L" file(s)." << std::endl;
}

bool run_with_timeout(const std::wstring& exe_path,
                      const std::wstring& arguments,
                      int timeout_seconds)
{
    std::wstring cmdline = L"\"" + exe_path + L"\" " + arguments;

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { nullptr };

    BOOL created = CreateProcessW(
        nullptr,               // lpApplicationName
        &cmdline[0],           // lpCommandLine
        nullptr,               // lpProcessAttributes
        nullptr,               // lpThreadAttributes
        FALSE,                 // bInheritHandles
        0,                     // dwCreationFlags
        nullptr,               // lpEnvironment
        nullptr,               // lpCurrentDirectory
        &si,
        &pi
    );

    if (!created) {
        DWORD err = GetLastError();
        std::wcerr << L"  [ERROR] CreateProcess failed, error " << err << std::endl;
        return false;
    }

    DWORD wait_result = WaitForSingleObject(pi.hProcess, timeout_seconds * 1000);

    bool success = false;
    if (wait_result == WAIT_OBJECT_0) {
        DWORD exit_code = 0;
        if (GetExitCodeProcess(pi.hProcess, &exit_code)) {
            success = (exit_code == 0);
            if (!success) {
                std::wcerr << L"  [WARN] Child process exited with code " << exit_code << std::endl;
            }
        } else {
            std::wcerr << L"  [ERROR] Cannot get exit code" << std::endl;
        }
    } else if (wait_result == WAIT_TIMEOUT) {
        std::wcerr << L"  [ERROR] Timeout (" << timeout_seconds << L" sec) exceeded, terminating process..." << std::endl;
        TerminateProcess(pi.hProcess, 1);
        success = false;
    } else {
        std::wcerr << L"  [ERROR] WaitForSingleObject failed, error " << GetLastError() << std::endl;
        TerminateProcess(pi.hProcess, 1);
        success = false;
    }

    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return success;
}

int wmain(int argc, wchar_t* argv[]) {
    _setmode(_fileno(stdout), _O_U16TEXT);
    _setmode(_fileno(stderr), _O_U16TEXT);

    // Проверяем специальный режим --file
    if (argc >= 3 && wcscmp(argv[1], L"--file") == 0) {
        // Режим обработки одного файла (для дочернего процесса)
        fs::path pdf_path(argv[2]);
        std::vector<std::string> patterns;
        std::string pattern = (argc >= 4) ? wstring_to_utf8(argv[3]) : "PATCH2";
        patterns.push_back(pattern);

        fs::path output_dir;
        if (argc >= 5) {
            output_dir = fs::path(argv[4]);
        }

        if (!fs::exists(pdf_path) || !fs::is_regular_file(pdf_path)) {
            std::wcerr << L"Invalid file: " << pdf_path.wstring() << std::endl;
            return 1;
        }
        process_pdf(pdf_path, patterns, output_dir);
        return 0;
    }

    if (argc < 2) {
        std::wcerr << L"Usage:\n"
                   << L"  barcodes.exe <path> [pattern] [output_dir]\n"
                   << L"  barcodes.exe --file <pdf_file> [pattern] [output_dir]\n"
                   << L"  <path>      - PDF file or directory\n"
                   << L"  [pattern]   - barcode pattern (default: PATCH2)\n"
                   << L"  [output_dir]- output directory for split parts (optional)\n";
        return 1;
    }

    fs::path input_path(argv[1]);
    std::vector<std::string> patterns;
    std::string pattern = (argc >= 3) ? wstring_to_utf8(argv[2]) : "PATCH2";
    patterns.push_back(pattern);

    fs::path output_dir;
    if (argc >= 4) {
        output_dir = fs::path(argv[3]);
    }

    if (!fs::exists(input_path)) {
        std::wcerr << L"Path does not exist: " << input_path.wstring() << std::endl;
        return 1;
    }

    if (fs::is_regular_file(input_path)) {
        std::wstring ext = input_path.extension().wstring();
        std::transform(ext.begin(), ext.end(), ext.begin(), ::towlower);
        if (ext != L".pdf") {
            std::wcerr << L"File is not a PDF: " << input_path.wstring() << std::endl;
            return 1;
        }
        process_pdf(input_path, patterns, output_dir);
        std::wcout << L"\nPress Enter to exit..." << std::endl;
        std::cin.get();
        return 0;
    }

    if (fs::is_directory(input_path)) {
        std::wcout << L"Searching for PDF files in: " << input_path.wstring() << std::endl
                   << L"Timeout per file: 60 seconds." << std::endl;

        wchar_t exe_path[MAX_PATH];
        GetModuleFileNameW(nullptr, exe_path, MAX_PATH);

        int success_count = 0;
        int fail_count = 0;
        int timeout_count = 0;

        for (const auto& entry : fs::recursive_directory_iterator(input_path)) {
            if (entry.is_regular_file()) {
                std::wstring ext = entry.path().extension().wstring();
                std::transform(ext.begin(), ext.end(), ext.begin(), ::towlower);
                if (ext == L".pdf") {
                    std::wcout << L"\n--- Processing: " << entry.path().wstring() << L" ---" << std::endl;

                    std::wstring args = L"--file \"" + entry.path().wstring() + L"\"";
                    args += L" \"" + utf8_to_wstring(pattern) + L"\"";
                    if (!output_dir.empty()) {
                        args += L" \"" + output_dir.wstring() + L"\"";
                    }

                    bool ok = run_with_timeout(exe_path, args, 60); 
                    if (ok) {
                        ++success_count;
                        std::wcout << L"  [OK] Processed successfully." << std::endl;
                    } else {
                        ++fail_count;
                        std::wcout << L"  [FAIL] Processing failed or timed out." << std::endl;
                    }
                }
            }
        }

        std::wcout << L"\n=== Summary ===" << std::endl;
        std::wcout << L"Success: " << success_count << std::endl;
        std::wcout << L"Failures: " << fail_count << std::endl;
        std::wcout << L"Total PDFs: " << (success_count + fail_count) << std::endl;
        std::wcout << L"\nPress Enter to exit..." << std::endl;
        std::cin.get();
        return 0;
    }

    std::wcerr << L"Unsupported path type: " << input_path.wstring() << std::endl;
    return 1;
}