import pvlib
import pandas as pd
from python.constants import REFERENCE_MODULE, SAPM_MODULES



def get_sapm_modules() -> list[str]:
    return list(map(lambda n: f"{n['module']} - {n['mounting']}", SAPM_MODULES))

def get_sapm_module(find_string: str) -> dict:
    module, mounting = find_string.split(" - ")
    
    find_list = filter(
        lambda n: n['module'] == module.strip() and n['mounting'] == mounting.strip(),
        SAPM_MODULES
    )
    
    return next(find_list) 

def calc_power_output(irradiation, temperature) -> float | list[float]:
    return_value = []
    
    try:
        for irr, tp in zip(irradiation, temperature):
            return_value.append(calc_power_output(irr, tp))
        
        return return_value
    except TypeError:
        efficiency = REFERENCE_MODULE['EFFICIENCY']
        temp_coefficient = REFERENCE_MODULE['TEMPERATURE_COEFFICIENT']
        reference_temp = REFERENCE_MODULE['REFERENCE_TEMPERATURE']
        panel_area = REFERENCE_MODULE['SINGLE_PANEL_AREA']
        
        delta_temp = temperature - reference_temp
        
        real_efficiency = efficiency * (1 + (temp_coefficient * delta_temp))
        
        return irradiation * panel_area * real_efficiency

def predict_panel_area(
        required_kwh_energy: float,
        date_range: tuple,
        surface_tilt: float,
        surface_azimuth: float,
        sapm_values: dict,
        latitude: float,
        longitude: float,
        altitude: float,
        timezone: str = "UTC",
        use_avg_temp: bool = True
    ) -> dict:
    
    location = pvlib.location.Location(latitude, longitude, timezone, altitude)

    # Define the time range
    times = pd.date_range(date_range[0], date_range[1], freq='h', tz=location.tz)
    
    # Calculate the solar position and clear-sky props
    solar_position = location.get_solarposition(times)
    clear_sky_props = location.get_clearsky(times)

    # Calculate the irradiance
    poa_irradiance = pvlib.irradiance.get_total_irradiance(
        surface_tilt=       surface_tilt,
        surface_azimuth=    surface_azimuth,
        dni=                clear_sky_props["dni"],
        ghi=                clear_sky_props["ghi"],
        dhi=                clear_sky_props["dhi"],
        solar_zenith=       solar_position['apparent_zenith'],
        solar_azimuth=      solar_position['azimuth']
    )['poa_global']
    
    # TODO: Implement the use of weather API to get the temperature
    air_temperature = REFERENCE_MODULE['REFERENCE_TEMPERATURE']

    # Get cell temperature for every checkpoint
    cell_temperature = pvlib.temperature.sapm_cell(
        poa_global=     poa_irradiance, 
        temp_air=       air_temperature,
        wind_speed=     1, 
        a=              sapm_values['a'], 
        b=              sapm_values['b'], 
        deltaT=         sapm_values['delta_t']
    )

    power_output = calc_power_output(poa_irradiance, cell_temperature)

    # Calculate total energy output (kWh)
    total_energy_output = sum(power_output) * 1e-3  # convert W to kW

    # Calculate the required panel area
    panel_area = (required_kwh_energy / total_energy_output) * REFERENCE_MODULE['SINGLE_PANEL_AREA']

    return {
        "panel_area": REFERENCE_MODULE['SINGLE_PANEL_AREA'],
        "total_area": panel_area,
        "total_kWh_output": total_energy_output,
        "wh_output": power_output,
        "cell_temperature": cell_temperature.to_list(),
    }
