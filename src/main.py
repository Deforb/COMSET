import logging
import random
import configparser
import importlib

from comset.COMSETsystem.Configuration import Configuration
from comset.COMSETsystem.Simulator import Simulator


def main():
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    try:
        # 读取配置文件
        config = configparser.ConfigParser()
        config.read("etc/config.properties")

        # 获取配置参数
        map_json_file = config.get("comset", "map_JSON_file").strip()
        dataset_file = config.get("comset", "dataset_file").strip()
        number_of_agents = int(config.get("comset", "number_of_agents"))
        bounding_polygon_kml_file = config.get(
            "comset", "bounding_polygon_KML_file"
        ).strip()
        
        agent_class_name = config.get("comset", "agent_class").strip()
        resource_maximum_life_time = int(
            config.get("comset", "resource_maximum_life_time")
        )

        # 可选参数
        dynamic_traffic = config.getboolean("comset", "dynamic_traffic", fallback=False)
        traffic_pattern_epoch = int(
            config.get("comset", "traffic_pattern_epoch", fallback=900)
        )
        traffic_pattern_step = int(
            config.get("comset", "traffic_pattern_step", fallback=60)
        )
        display_logging = config.getboolean("comset", "logging", fallback=False)
        if display_logging:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)

        # 设置随机种子
        agent_placement_seed = config.getint(
            "comset", "agent_placement_seed", fallback=-1
        )
        if agent_placement_seed < 0:
            agent_placement_seed = random.randint(0, 2**32 - 1)

            # 动态加载代理类
        module_name, class_name = agent_class_name.rsplit(".", 1)
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)

        # 配置模拟器
        Configuration.make(
            agent_class,
            map_json_file,
            dataset_file,
            number_of_agents,
            bounding_polygon_kml_file,
            resource_maximum_life_time,
            agent_placement_seed,
            dynamic_traffic,
            traffic_pattern_epoch,
            traffic_pattern_step,
        )

        # 创建并运行模拟器
        simulator = Simulator(Configuration.get())
        simulator.run()

    except Exception as e:
        logging.error(f"发生错误: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()
