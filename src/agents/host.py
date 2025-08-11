import re
from .base_agent import Agent
from utils.register import register_class, registry


@register_class(alias="Agent.Host.GPT")
class Host(Agent):
    def __init__(self, args, host_info=None):
        engine = registry.get_class("Engine.GPT")(
            openai_api_key=args.host_openai_api_key,
            openai_api_base=args.host_openai_api_base,
            openai_model_name=args.host_openai_model_name,
            temperature=args.host_temperature,
            max_tokens=args.host_max_tokens,
            top_p=args.host_top_p,
            frequency_penalty=args.host_frequency_penalty,
            presence_penalty=args.host_presence_penalty
        )
        self.system_message = host_info or "你是医院的数据库管理员，负责收集、汇总和整理病人的病史和检查数据。\n"
        super().__init__(engine)

    @staticmethod
    def add_parser_args(parser):
        parser.add_argument('--host_openai_api_key', type=str, help='API key for OpenAI')
        parser.add_argument('--host_openai_api_base', type=str, help='API base for OpenAI')
        parser.add_argument('--host_openai_model_name', type=str, help='API model name for OpenAI')
        parser.add_argument('--host_temperature', type=float, default=0.0, help='temperature')
        parser.add_argument('--host_max_tokens', type=int, default=2048, help='max tokens')
        parser.add_argument('--host_top_p', type=float, default=1, help='top p')
        parser.add_argument('--host_frequency_penalty', type=float, default=0, help='frequency penalty')
        parser.add_argument('--host_presence_penalty', type=float, default=0, help='presence penalty')

    def memorize(self, message):
        self.memories.append(message)

    def forget(self):
        self.memories = [("system", self.system_message)]

    def speak(self, content):
        messages = [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": "您好，我需要做基因组测序，能否告诉我这些检查结果？"},
            {"role": "assistant", "content": "#检查项目#\n-基因组测序: 无异常"},
            {"role": "user", "content": content}
        ]
        return self.engine.get_response(messages)

    def _build_doctor_list_str(self, doctors, use_char=False):
        if use_char:
            names = ["##医生{}##".format(chr(65 + i)) for i in range(len(doctors))]
        else:
            names = ["##医生{}##".format(doctor.name) for doctor in doctors]
        if len(names) > 2:
            return "、".join(names[:-2]) + "、" + names[-2] + "和" + names[-1]
        return names[0] + "和" + names[1]

    def _collect_diagnoses(self, doctors, patient, use_char=False):
        parts = []
        for i, doctor in enumerate(doctors):
            doctor_label = chr(65 + i) if use_char else doctor.name
            parts.append(
                f"##医生{doctor_label}##\n\n"
                f"#诊断结果#\n{doctor.get_diagnosis_by_patient_id(patient.id, '诊断结果')}\n\n"
                f"#诊断依据#\n{doctor.get_diagnosis_by_patient_id(patient.id, '诊断依据')}\n\n"
                f"#治疗方案#\n{doctor.get_diagnosis_by_patient_id(patient.id, '治疗方案')}\n\n"
            )
        return "".join(parts)

    def summarize_diagnosis(self, doctors, patient):
        diagnosis_text = self._collect_diagnoses(doctors, patient, use_char=True)
        doctor_names = self._build_doctor_list_str(doctors, use_char=True)

        system_message = (
            f"你是一个资深的#主任医生#。\n"
            f"你正在主持一场医生针对患者病情的会诊，参与的医生有{doctor_names}。\n"
            f"病人的基本情况如下：\n"
            f"#症状#\n{doctors[0].get_diagnosis_by_patient_id(patient.id, '症状')}\n\n"
            f"#辅助检查#\n{doctors[0].get_diagnosis_by_patient_id(patient.id, '辅助检查')}\n\n"
            "(1) 你需要听取每个医生的诊断报告，其中包含对病人的#诊断结果#、#诊断依据#和#治疗方案#。\n"
            "(2) 你需要汇总每个医生的信息，给出对病人的最终诊断。\n\n"
            "(3) 请你按照下面的格式来进行输出。\n"
            "#诊断结果#\n(1) xxx\n(2) xxx\n\n"
            "#诊断依据#\n(1) xxx\n(2) xxx\n\n"
            "#治疗方案#\n(1) xxx\n(2) xxx\n"
        )

        return self.engine.get_response([
            {"role": "system", "content": system_message},
            {"role": "user", "content": diagnosis_text}
        ])

    def measure_agreement(self, doctors, patient, discussion_mode="Parallel"):
        diagnosis_text = self._collect_diagnoses(doctors, patient)
        doctor_names = self._build_doctor_list_str(doctors)

        base_message = (
            f"你是一个资深的主任医生。\n"
            f"你正在主持一场医生针对患者病情的会诊，参与的医生有{doctor_names}。\n"
            f"病人的基本情况如下：\n"
            f"#症状#\n{doctors[0].get_diagnosis_by_patient_id(patient.id, '症状')}\n\n"
            f"#辅助检查#\n{doctors[0].get_diagnosis_by_patient_id(patient.id, '辅助检查')}\n\n"
        )

        system_message = base_message + (
            "你需要听取每个医生的诊断报告，其中包含对病人的#诊断结果#、#诊断依据#和#治疗方案#。\n\n"
            "请你按照下面的格式来进行输出。\n"
            "(1) 如果医生之间已经达成一致，请你输出：\n#结束#\n\n"
            "(2) 如果医生之间没有达成一致，请你输出：\n#继续#"
        )

        judgement = self.engine.get_response([
            {"role": "system", "content": system_message},
            {"role": "user", "content": diagnosis_text}
        ])

        if "#结束#" in judgement:
            return "#结束#"
        elif "#继续#" in judgement:
            if discussion_mode == "Parallel":
                return "#继续#"
            elif discussion_mode == "Parallel_with_Critique":
                critique_message = base_message + (
                    "(1) 你需要听取每个医生的诊断报告，其中包含对病人的#诊断结果#、#诊断依据#和#治疗方案#。\n"
                    "(2) 请你按照重要性列出最多3个需要讨论的争议点，按照下面的格式输出：\n"
                    "(a) xxx\n(b) xxx\n"
                )
                critique = self.engine.get_response([
                    {"role": "system", "content": critique_message},
                    {"role": "user", "content": diagnosis_text}
                ])
                return re.sub('.*\(a\)', '(a)', critique, flags=re.DOTALL)
        else:
            raise Exception(judgement)
