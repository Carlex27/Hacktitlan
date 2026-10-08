// Evita una consola adicional en Windows para compilaciones de release.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    hacktitlan_desktop_lib::run()
}
