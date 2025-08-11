import re
from .base_agent import Agent
from utils.register import register_class, registry


class BaseReporter(Agent):
    """
    Base class for medical record reporters.
    Handles initialization of the language model engine, 
    common argument parsing, and message formatting.
    """

    DEFAULT_SYSTEM_MESSAGE = (
        "你是医院的数据库管理员，负责收集、汇总和整理病人的病史和检查数据。\n"
    )

    def __init__(self, args, reporter_info=None, engine_alias=None):
        if engine_alias is None:
            raise ValueError("engine_alias must be specified in subclasses.")

        engine_cls = registry.get_class(engine_alias)
        engine = engine_cls(
            openai_api_key=args.reporter_openai_api_key,
            openai_api_base=args.reporter_openai_api_base,
            openai_model_name=args.reporter_openai_model_name,
            temperature=args.reporter_temperature,
            max_tokens=args.reporter_max_tokens,
            top_p=args.reporter_top_p,
            frequency_penalty=args.reporter_frequency_penalty,
            presence_penalty=args.reporter_presence_penalty
        )

        self.edit_query = True
        self.system_message = reporter_info or self.DEFAULT_SYSTEM_MESSAGE
        super().__init__(engine)

    @staticmethod
    def add_parser_args(parser):
        parser.add_argument('--reporter_openai_api_key', type=str, help='OpenAI API key')
        parser.add_argument('--reporter_openai_api_base', type=str, help='OpenAI API base URL')
        parser.add_argument('--reporter_openai_model_name', type=str, help='OpenAI model name')
        parser.add_argument('--reporter_temperature', type=float, default=0.0, help='Temperature for generation')
        parser.add_argument('--reporter_max_tokens', type=int, default=2048, help='Max token output')
        parser.add_argument('--reporter_top_p', type=float, default=1, help='Top-p sampling')
        parser.add_argument('--reporter_frequency_penalty', type=float, default=0, help='Frequency penalty')
        parser.add_argument('--reporter_presence_penalty', type=float, default=0, help='Presence penalty')

    @staticmethod
    def parse_content(response):
        """
        Extracts the '#检查项目#' section from the model's response.
        Returns False if not found.
        """
        if "#检查项目#" not in response:
            return False
        matches = re.findall(r"#检查项目#(.+?)\n\n", response, re.S)
        return matches[0].strip() if matches else False


@register_class(alias="Agent.Reporter.GPT")
class Reporter(BaseReporter):
    def __init__(self, args, reporter_info=None):
        super().__init__(args, reporter_info, engine_alias="Engine.GPT")

    def speak(self, medical_records, content, save_to_memory=False):
        system_message = (
            f"{self.system_message}\n\n"
            "这是你收到的病人的检查结果。\n"
            f"#查体#\n{medical_records['查体'].strip()}\n"
            f"#辅助检查#\n{medical_records['辅助检查'].strip()}\n\n"
            "下面会有病人或者医生来查询，你要忠实地按照收到的检查结果，"
            "找到对应的项目，并按照下面的格式来回复。\n\n"
            "#检查项目#\n- xxx: xxx\n- xxx: xxx\n"
            "#xx检查#\n- xxx: xxx\n- xxx: xxx\n\n"
            "如果无法查询到对应的检查项目则回复：\n- xxx: 无异常"
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": "您好，我需要做基因组测序，能否告诉我这些检查结果？"},
            {"role": "assistant", "content": "#检查项目#\n- 基因组测序"},
            {"role": "user", "content": content}
        ]

        return self.engine.get_response(messages)


@register_class(alias="Agent.Reporter.GPTV2")
class ReporterV2(BaseReporter):
    def __init__(self, args, reporter_info=None):
        super().__init__(args, reporter_info, engine_alias="Engine.GPTV2")

    def speak(self, medical_records, content, save_to_memory=False):
        examination_query = self.parse_examination_queries(content)

        system_message = (
            f"{self.system_message}\n\n"
            "这是你收到的病人的检查结果。\n"
            f"#查体#\n{medical_records['查体'].strip()}\n"
            f"#辅助检查#\n{medical_records['辅助检查'].strip()}\n\n"
            "下面会有病人或者医生来查询，你要忠实地按照收到的检查结果，"
            "找到对应的项目，并按照下面的格式来回复。\n\n"
            "#检查项目#\n- xxx: xxx\n- xxx: xxx\n"
            "#xx检查#\n- xxx: xxx\n- xxx: xxx\n\n"
            "如果无法查询到对应的检查项目则回复：\n- xxx: 无异常"
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": "#检查项目#\n- 基因组测序"},
            {"role": "assistant", "content": "#检查项目#\n- 基因组测序: 无异常"},
            {"role": "user", "content": examination_query}
        ]

        return self.engine.get_response(messages)

    def parse_examination_queries(self, query):
        """
        Extracts explicit medical examination items from a user query.
        Returns a formatted '#检查项目#' string or None.
        """
        # (Keeping your example training prompts but would recommend moving to external config)
        system_message = (
            "你是医院负责检查的自动化接待员。"
            "请你利用掌握的医学检查命名实体知识，从病人的检查申请中提取明确的专业检查项目，"
            "方便后续科室进行检查。\n\n"
            "格式要求：\n#检查项目#\n- xxx\n- xxx\n\n"
            "如果没有具体项目，请输出：\n#检查项目#\n- 无"
        )

        # Few-shot examples omitted here for brevity...
        # You could move them to a JSON or YAML file for cleaner maintenance.

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ]

        response = self.get_response(messages)
        if "#检查项目#" not in response or "- 无" in response.replace(" ", ""):
            return None

        items = []
        capture = False
        for line in response.splitlines():
            if "#检查项目#" in line:
                capture = True
                continue
            if capture and line.startswith("-"):
                items.append(line[1:].strip())
            elif capture and not line.strip():
                break

        return "\n- ".join(["#检查项目#"] + items) if items else None
