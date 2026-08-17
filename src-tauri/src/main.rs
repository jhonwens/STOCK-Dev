#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod license;
mod feature_flag;
// ⚠️ Plan 修订 (Batch 2 #2): 这两个 mod 必须在 main.rs 顶部注册（不是 commands.rs）
// 现有 main.rs 已有 mod commands; mod license; mod feature_flag;
mod agent_commands;
mod agent_bridge;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let handle = app.handle().clone();

            // --- 生产模式（打包后 .app bundle）初始化 ---
            #[cfg(not(debug_assertions))]
            {
                // 1. 把资源目录设为 APP_ROOT，Python 脚本/数据路径都基于此
                if let Ok(resource_dir) = app.path().resource_dir() {
                    commands::init_app_root(Some(resource_dir.clone()));
                    std::env::set_var("STOCK_PROJECT_ROOT", &resource_dir);
                    // 设置 STOCK_BACKEND_RUNNER 指向 PyInstaller 编译后的独立可执行文件
                    // 后端会优先使用它而不是回退到 python3 entry.py（系统 Python 缺少依赖）
                    #[cfg(target_os = "windows")]
                    let runner_name = "backend-runner.exe";
                    #[cfg(not(target_os = "windows"))]
                    let runner_name = "backend-runner";
                    let runner_path = resource_dir.join(runner_name);
                    if runner_path.exists() {
                        std::env::set_var("STOCK_BACKEND_RUNNER", &runner_path);
                    }
                }

                // 2. 数据库和配置存到 ~/Library/Application Support/com.hengshi-value.app/
                if let Ok(data_dir) = app.path().app_data_dir() {
                    std::fs::create_dir_all(&data_dir).ok();
                    // 首次启动创建空的 llm_config.json
                    let config_path = data_dir.join("llm_config.json");
                    if !config_path.exists() {
                        std::fs::write(&config_path, "[]").ok();
                    }
                    std::env::set_var("STOCK_DB_PATH", data_dir.join("stock_data.db"));
                    std::env::set_var("STOCK_CONFIG_DIR", &data_dir);
                    std::env::set_var("STOCK_LIST_PATH", data_dir.join("stock_list.yaml"));
                }
            }

            // --- macOS 标题栏代理图标修复（延迟等窗口就绪）---
            let mac_handle = handle.clone();
            std::thread::spawn(move || {
                std::thread::sleep(std::time::Duration::from_millis(1000));
                let _ = handle.run_on_main_thread(move || {
                    #[cfg(target_os = "macos")]
                    if let Some(win) = mac_handle.get_webview_window("main") {
                        if let Ok(ptr) = win.ns_window() {
                            use objc2::rc::Retained;
                            use objc2_app_kit::NSWindow;
                            use objc2_foundation::NSURL;
                            let ns_window: Retained<NSWindow> = unsafe { Retained::retain(ptr.cast()).unwrap() };
                            let bundle_path = std::env::current_exe()
                                .ok()
                                .and_then(|p| {
                                    let mut p = p.clone();
                                    for _ in 0..3 { p.pop(); }
                                    if p.extension().map_or(false, |e| e == "app") { Some(p) } else { None }
                                });
                            if let Some(path) = bundle_path {
                                if let Some(url) = NSURL::from_directory_path(path) {
                                    ns_window.setRepresentedURL(Some(&url));
                                }
                            }
                        }
                    }
                });
            });
            Ok(())
        })
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            commands::get_dashboard_summary,
            commands::get_market_movers,
            commands::get_stock_list,
            commands::get_portfolio,
            commands::get_technical_indicators,
            commands::run_analysis,
            commands::run_llm_analysis,
            commands::save_llm_config,
            commands::load_llm_config,
            commands::list_llm_models,
            commands::save_llm_model,
            commands::delete_llm_model,
            commands::set_active_llm_model,
            commands::test_llm_connection,
            commands::add_stock_to_list,
            commands::remove_stock_from_list,
            commands::batch_add_stocks,
            commands::batch_remove_stocks,
            commands::get_portfolio_stocks,
            commands::add_portfolio_stock,
            commands::remove_portfolio_stock,
            commands::run_portfolio_llm,
            commands::save_portfolio_analysis,
            commands::load_portfolio_analysis,
            commands::export_portfolio_md,
            commands::run_candidate_llm,
            commands::save_candidate_analysis,
            commands::load_candidate_analysis,
            commands::export_candidate_md,
            commands::search_stock,
            commands::run_stock_insight,
            commands::save_stock_insight,
            commands::load_stock_insight,
            commands::export_stock_insight_md,
            commands::get_feature_flags,
            commands::activate_license,
            commands::deactivate_license,
            commands::get_license_info,
            // 智能分析 Agent commands (Batch 2 Task 7)
            agent_commands::agent_create_session,
            agent_commands::agent_list_sessions,
            agent_commands::agent_rename_session,
            agent_commands::agent_delete_session,
            agent_commands::agent_pin_session,
            agent_commands::agent_get_messages,
            // Task 8: 流式消息发送
            agent_commands::agent_send_message,
            // Task 14: 报告导出 (MD/HTML)
            agent_commands::agent_export,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}