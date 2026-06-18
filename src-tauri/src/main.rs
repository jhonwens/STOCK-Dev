#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod license;
mod feature_flag;

fn main() {
    tauri::Builder::default()
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
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}